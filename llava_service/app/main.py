import asyncio
import io
import logging
import os
import time
from functools import lru_cache

import torch
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from transformers import AutoProcessor, BitsAndBytesConfig, LlavaForConditionalGeneration

logger = logging.getLogger("llava_service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


class AnalyzeResponse(BaseModel):
    description: str


class BatchAnalyzeItem(BaseModel):
    filename: str | None = None
    description: str


class BatchAnalyzeResponse(BaseModel):
    images: list[BatchAnalyzeItem]


app = FastAPI(title="llava-service")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _auth_header(token: str) -> str:
    return f"Bearer {token}"


def _validate_auth(authorization: str | None) -> None:
    expected_token = os.getenv("LLAVA_AUTH_TOKEN", "").strip()
    if expected_token and authorization != _auth_header(expected_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


@lru_cache(maxsize=1)
def get_runtime():
    started_at = time.monotonic()
    model_id = os.getenv("LLAVA_MODEL_ID", "llava-hf/llava-1.5-7b-hf")
    has_cuda = torch.cuda.is_available()
    load_in_4bit = _env_bool("LLAVA_LOAD_IN_4BIT", True) and has_cuda
    dtype = torch.float16 if has_cuda else torch.float32
    device_map = "auto" if has_cuda else None

    if not has_cuda:
        logger.warning("CUDA is not available. Loading LLaVA on CPU; inference will be slow.")

    quantization_config = None
    if load_in_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=dtype,
        )

    logger.info("Loading LLaVA model %s", model_id)
    processor = AutoProcessor.from_pretrained(model_id)
    model = LlavaForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map=device_map,
        quantization_config=quantization_config,
    )
    if not has_cuda:
        model = model.to("cpu")

    logger.info("LLaVA model loaded in %.2fs", time.monotonic() - started_at)
    return processor, model


@app.get("/health")
def health():
    return {
        "status": "ok",
        "cuda_available": torch.cuda.is_available(),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    image: UploadFile = File(...),
    prompt: str = Form(..., min_length=1),
    authorization: str | None = Header(default=None),
):
    _validate_auth(authorization)
    pil_image = await _read_image(image)
    description = await _generate_with_timeout(pil_image, prompt)
    return AnalyzeResponse(description=description)


@app.post("/analyze/batch", response_model=BatchAnalyzeResponse)
async def analyze_batch(
    images: list[UploadFile] = File(...),
    prompt: str = Form(..., min_length=1),
    authorization: str | None = Header(default=None),
):
    _validate_auth(authorization)
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required.")
    if len(images) > 16:
        raise HTTPException(status_code=400, detail="Batch size must not exceed 16 images.")

    results: list[BatchAnalyzeItem] = []
    for image in images:
        pil_image = await _read_image(image)
        description = await _generate_with_timeout(pil_image, prompt)
        results.append(BatchAnalyzeItem(filename=image.filename, description=description))
    return BatchAnalyzeResponse(images=results)


async def _read_image(image: UploadFile) -> Image.Image:
    content_type = (image.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"Invalid content type: {image.content_type}")

    try:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Image file is empty.")
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid image file.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc


async def _generate_with_timeout(image: Image.Image, prompt: str) -> str:
    timeout = _env_int("LLAVA_GENERATION_TIMEOUT_SECONDS", 180)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_generate_description, image, prompt),
            timeout=timeout,
        )
    except TimeoutError as exc:
        logger.exception("LLaVA generation timed out after %ss", timeout)
        raise HTTPException(status_code=504, detail="LLaVA generation timed out.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("LLaVA generation failed")
        raise HTTPException(status_code=500, detail=f"LLaVA generation failed: {exc}") from exc


def _generate_description(pil_image: Image.Image, prompt: str) -> str:
    processor, model = get_runtime()
    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    prompt_text = processor.apply_chat_template(conversation, add_generation_prompt=True)

    inputs = processor(text=prompt_text, images=pil_image, return_tensors="pt")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}

    max_new_tokens = _env_int("LLAVA_MAX_NEW_TOKENS", 256)
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=max_new_tokens)

    prompt_tokens = inputs["input_ids"].shape[1]
    generated_trimmed = generated[:, prompt_tokens:]
    return processor.batch_decode(
        generated_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )[0].strip()

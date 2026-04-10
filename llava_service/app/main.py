import io
import os
from functools import lru_cache

import torch
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel
from transformers import AutoProcessor, BitsAndBytesConfig, LlavaForConditionalGeneration


class AnalyzeResponse(BaseModel):
    description: str


app = FastAPI(title="llava-service")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _auth_header(token: str) -> str:
    return f"Bearer {token}"


@lru_cache(maxsize=1)
def get_runtime():
    model_id = os.getenv("LLAVA_MODEL_ID", "llava-hf/llava-1.5-7b-hf")
    load_in_4bit = _env_bool("LLAVA_LOAD_IN_4BIT", True)
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    quantization_config = None
    if load_in_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=dtype,
        )

    processor = AutoProcessor.from_pretrained(model_id)
    model = LlavaForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map="auto",
        quantization_config=quantization_config,
    )
    return processor, model


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    authorization: str | None = Header(default=None),
):
    expected_token = os.getenv("LLAVA_AUTH_TOKEN", "").strip()
    if expected_token and authorization != _auth_header(expected_token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        image_bytes = await image.read()
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

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
    prompt_text = processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
    )

    inputs = processor(
        text=prompt_text,
        images=pil_image,
        return_tensors="pt",
    )
    inputs = {key: value.to(model.device) for key, value in inputs.items()}

    max_new_tokens = int(os.getenv("LLAVA_MAX_NEW_TOKENS", "256"))
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=max_new_tokens)

    prompt_tokens = inputs["input_ids"].shape[1]
    generated_trimmed = generated[:, prompt_tokens:]
    description = processor.batch_decode(
        generated_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )[0].strip()

    return AnalyzeResponse(description=description)

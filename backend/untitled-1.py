import argparse
import random
import struct
import zlib
from pathlib import Path

from PIL import Image


MAGIC = b"CVZ2"
DEFAULT_DIR = Path(r"C:\Users\Dariia\Desktop\lr6")
DEFAULT_SOURCE_IMAGE = DEFAULT_DIR / "cat.jpg"
DEFAULT_TEXT_FILE = DEFAULT_DIR / "cvz.txt"
DEFAULT_WATERMARKED_IMAGE = DEFAULT_DIR / "cat1.png"
DEFAULT_RECOVERED_TEXT = DEFAULT_DIR / "cvz1.txt"

MAX_REPEAT_COUNT = 7
MIN_REPEAT_COUNT = 3
CELL_SIZE = 1
CHANNEL_DELTA = 56
DECISION_MARGIN = 6


def bytes_to_bits(data: bytes) -> list[int]:
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def bits_to_bytes(bits: list[int]) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError("Bit count must be divisible by 8.")
    data = bytearray()
    for i in range(0, len(bits), 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        data.append(value)
    return bytes(data)


def repeat_bits(bits: list[int], repeat_count: int) -> list[int]:
    repeated = []
    for bit in bits:
        repeated.extend([bit] * repeat_count)
    return repeated


def majority_decode(bits: list[int], repeat_count: int) -> list[int]:
    if len(bits) % repeat_count != 0:
        raise ValueError("Repeated bits are damaged.")
    decoded = []
    for i in range(0, len(bits), repeat_count):
        chunk = bits[i:i + repeat_count]
        decoded.append(1 if sum(chunk) > repeat_count // 2 else 0)
    return decoded


def clamp(value: int) -> int:
    return max(0, min(255, value))


def build_payload(text: str) -> bytes:
    raw = text.encode("utf-8")
    crc = zlib.crc32(raw) & 0xFFFFFFFF
    return MAGIC + struct.pack(">I", len(raw)) + struct.pack(">I", crc) + raw


def build_framed_payload(text: str, repeat_count: int) -> bytes:
    return bytes([repeat_count]) + build_payload(text)


def parse_payload(payload: bytes) -> str:
    if len(payload) < 13:
        raise ValueError("Payload is too short.")
    if payload[1:5] != MAGIC:
        raise ValueError("Magic not found.")

    raw_len = struct.unpack(">I", payload[5:9])[0]
    expected_crc = struct.unpack(">I", payload[9:13])[0]
    raw = payload[13:13 + raw_len]
    if len(raw) != raw_len:
        raise ValueError("Payload is truncated.")

    actual_crc = zlib.crc32(raw) & 0xFFFFFFFF
    if actual_crc != expected_crc:
        raise ValueError("CRC mismatch.")
    return raw.decode("utf-8")


def recover_best_effort_text(payload: bytes) -> str:
    if len(payload) < 13:
        return payload.decode("utf-8", errors="replace")
    if payload[1:5] != MAGIC:
        return payload.decode("utf-8", errors="replace")

    raw_len = struct.unpack(">I", payload[5:9])[0]
    raw = payload[13:13 + raw_len]
    return raw.decode("utf-8", errors="replace")


def get_segments(width: int, height: int) -> list[tuple[int, int, int, int]]:
    start_y = int(height * 0.38)
    lower_start_y = int(height * 0.58)
    if height - start_y < 20:
        raise ValueError("Image is too small.")

    left_x0 = 0
    left_x1 = width // 2
    right_x0 = width // 2
    right_x1 = width

    return [
        (left_x0, start_y, left_x1, height),
        (right_x0, start_y, right_x1, height),
        (left_x0, lower_start_y, left_x1, height),
        (right_x0, lower_start_y, right_x1, height),
    ]


def get_positions(segment: tuple[int, int, int, int], key: str) -> list[tuple[int, int]]:
    x0, y0, x1, y1 = segment
    positions = []
    for y in range(y0, y1 - CELL_SIZE + 1, CELL_SIZE):
        for x in range(x0, x1 - CELL_SIZE + 1, CELL_SIZE):
            positions.append((x, y))
    rng = random.Random(f"{key}:{x0}:{y0}:{x1}:{y1}")
    rng.shuffle(positions)
    return positions


def choose_repeat_count(payload_bits_len: int, segments: list[tuple[int, int, int, int]], key: str) -> int:
    capacities = [len(get_positions(segment, key)) for segment in segments]
    min_capacity = min(capacities)
    for repeat_count in range(MAX_REPEAT_COUNT, MIN_REPEAT_COUNT - 1, -2):
        if payload_bits_len * repeat_count <= min_capacity:
            return repeat_count
    raise ValueError("Text is too long for this image.")


def write_cell_bit(image: Image.Image, x0: int, y0: int, bit: int) -> None:
    pixels = image.load()
    for y in range(y0, y0 + CELL_SIZE):
        for x in range(x0, x0 + CELL_SIZE):
            r, g, b = pixels[x, y]
            avg = (g + b) // 2
            if bit == 1:
                new_g = clamp(avg + CHANNEL_DELTA)
                new_b = clamp(avg - CHANNEL_DELTA)
            else:
                new_g = clamp(avg - CHANNEL_DELTA)
                new_b = clamp(avg + CHANNEL_DELTA)
            pixels[x, y] = (r, new_g, new_b)


def read_cell_bit(image: Image.Image, x0: int, y0: int) -> int:
    pixels = image.load()
    total_diff = 0
    count = 0
    for y in range(y0, y0 + CELL_SIZE):
        for x in range(x0, x0 + CELL_SIZE):
            _, g, b = pixels[x, y]
            total_diff += g - b
            count += 1
    avg_diff = total_diff / count
    return 1 if avg_diff >= 0 else 0


def extract_raw_probe_text(image: Image.Image, segment: tuple[int, int, int, int], repeat_count: int, key: str) -> str:
    positions = get_positions(segment, key)
    probe_cells = min(8000, len(positions))
    bits = [read_cell_bit(image, x, y) for x, y in positions[:probe_cells]]
    bits = bits[: len(bits) - (len(bits) % repeat_count)]
    if not bits:
        return ""
    decoded_bits = majority_decode(bits, repeat_count)
    decoded_bits = decoded_bits[: len(decoded_bits) - (len(decoded_bits) % 8)]
    if not decoded_bits:
        return ""
    return bits_to_bytes(decoded_bits).decode("utf-8", errors="replace")


def encode_image(image_path: Path, text_path: Path, output_path: Path, key: str) -> None:
    text = text_path.read_text(encoding="utf-8")
    image = Image.open(image_path).convert("RGB")
    segments = get_segments(*image.size)

    base_payload = build_payload(text)
    payload_bits_len = (1 + len(base_payload)) * 8
    repeat_count = choose_repeat_count(payload_bits_len, segments, key)
    payload = build_framed_payload(text, repeat_count)
    payload_bits = bytes_to_bits(payload)
    repeated_bits = repeat_bits(payload_bits, repeat_count)

    for segment in segments:
        positions = get_positions(segment, key)
        if len(repeated_bits) > len(positions):
            raise ValueError("Not enough space in the segment.")
        for (x, y), bit in zip(positions, repeated_bits):
            write_cell_bit(image, x, y, bit)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    print(f"Text embedded into {output_path}")
    print(f"repeat_count={repeat_count}")


def decode_image(image_path: Path, output_text_path: Path, key: str) -> None:
    image = Image.open(image_path).convert("RGB")
    segments = get_segments(*image.size)

    text_candidates = []
    fallback_candidates = []
    raw_candidates = []

    for segment in segments:
        positions = get_positions(segment, key)
        for repeat_count in range(MAX_REPEAT_COUNT, MIN_REPEAT_COUNT - 1, -2):
            try:
                raw_text = extract_raw_probe_text(image, segment, repeat_count, key)
                if raw_text:
                    raw_candidates.append(raw_text)

                header_cells = 13 * 8 * repeat_count
                if header_cells > len(positions):
                    continue

                header_bits_repeated = [read_cell_bit(image, x, y) for x, y in positions[:header_cells]]
                header_bits = majority_decode(header_bits_repeated, repeat_count)
                header = bits_to_bytes(header_bits)

                if header[0] != repeat_count or header[1:5] != MAGIC:
                    continue

                raw_len = struct.unpack(">I", header[5:9])[0]
                total_bytes = 13 + raw_len
                total_cells = total_bytes * 8 * repeat_count
                if total_cells > len(positions):
                    continue

                full_repeated = [read_cell_bit(image, x, y) for x, y in positions[:total_cells]]
                full_bits = majority_decode(full_repeated, repeat_count)
                payload = bits_to_bytes(full_bits)

                try:
                    text_candidates.append(parse_payload(payload))
                except Exception:
                    fallback_candidates.append(recover_best_effort_text(payload))
            except Exception:
                continue

    if text_candidates:
        best_text = max(set(text_candidates), key=text_candidates.count)
    elif fallback_candidates:
        best_text = max(fallback_candidates, key=len)
    elif raw_candidates:
        best_text = max(raw_candidates, key=len)
    else:
        best_text = "No text could be extracted."

    output_text_path.parent.mkdir(parents=True, exist_ok=True)
    output_text_path.write_text(best_text, encoding="utf-8")
    print(f"Text extracted into {output_text_path}")
    print(best_text)


def compare_texts(original_text_path: Path, extracted_text_path: Path) -> None:
    if not original_text_path.exists() or not extracted_text_path.exists():
        return
    original_text = original_text_path.read_text(encoding="utf-8")
    extracted_text = extracted_text_path.read_text(encoding="utf-8")
    if original_text == extracted_text:
        print("Texts match.")
    else:
        print("Texts differ.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Embed or extract text in image pixels.")
    subparsers = parser.add_subparsers(dest="mode")

    encode_parser = subparsers.add_parser("encode")
    encode_parser.add_argument("--image", type=Path, default=DEFAULT_SOURCE_IMAGE)
    encode_parser.add_argument("--text", type=Path, default=DEFAULT_TEXT_FILE)
    encode_parser.add_argument("--output", type=Path, default=DEFAULT_WATERMARKED_IMAGE)
    encode_parser.add_argument("--key", default="cvz_secret")

    decode_parser = subparsers.add_parser("decode")
    decode_parser.add_argument("--image", type=Path, default=DEFAULT_WATERMARKED_IMAGE)
    decode_parser.add_argument("--output", type=Path, default=DEFAULT_RECOVERED_TEXT)
    decode_parser.add_argument("--key", default="cvz_secret")
    decode_parser.add_argument("--source-text", type=Path, default=DEFAULT_TEXT_FILE)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.mode:
        mode = input("Choose mode (encode/decode): ").strip().lower()
        if mode not in {"encode", "decode"}:
            print("Enter encode or decode.")
            return
        args = parser.parse_args([mode])

    try:
        if args.mode == "encode":
            encode_image(args.image, args.text, args.output, args.key)
        elif args.mode == "decode":
            decode_image(args.image, args.output, args.key)
            compare_texts(args.source_text, args.output)
    except FileNotFoundError as error:
        print(f"File not found: {error.filename}")
    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()

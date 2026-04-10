from __future__ import annotations

import base64
import io

from PIL import Image

from geo_agent.config import settings


def load_image_bytes(source: str | bytes) -> bytes:
    if isinstance(source, bytes):
        return source
    with open(source, "rb") as f:
        return f.read()


def resize_image(image_bytes: bytes, max_size: int | None = None) -> bytes:
    max_size = max_size or settings.MAX_IMAGE_SIZE
    img = Image.open(io.BytesIO(image_bytes))
    if max(img.size) <= max_size:
        return image_bytes
    ratio = max_size / max(img.size)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img = img.resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    fmt = img.format or "JPEG"
    if fmt.upper() == "PNG":
        img.save(buf, format="PNG")
    else:
        img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def image_to_base64(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def detect_media_type(image_bytes: bytes) -> str:
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if image_bytes[:3] == b"GIF":
        return "image/gif"
    return "image/jpeg"

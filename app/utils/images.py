"""Изображения (Pillow)."""

from io import BytesIO

from PIL import Image


def resize_image(data: bytes, size: tuple[int, int] = (640, 480)) -> bytes:
    img = Image.open(BytesIO(data))
    img.thumbnail(size)
    out = BytesIO()
    img.convert("RGB").save(out, format="PNG")
    return out.getvalue()
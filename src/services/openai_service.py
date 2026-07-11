import base64
import io
from PIL import Image
import openai

MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"  # fallback only; callers should pass size explicitly


def _prepare_png_for_edit(image_path: str) -> bytes:
    """Convert image to RGBA PNG ≤ 4MB for the edit endpoint."""
    img = Image.open(image_path).convert("RGBA")
    # Resize if needed to keep under 4MB
    max_side = 1024
    if img.width > max_side or img.height > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # If still over 4MB, reduce quality further
    while buf.tell() > 4 * 1024 * 1024:
        max_side = int(max_side * 0.8)
        img.thumbnail((max_side, max_side), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
    return buf.getvalue()


def generate_image(api_key: str, prompt: str, size: str = DEFAULT_SIZE) -> bytes:
    client = openai.OpenAI(api_key=api_key)
    response = client.images.generate(
        model=MODEL,
        prompt=prompt,
        n=1,
        size=size,
    )
    return base64.b64decode(response.data[0].b64_json)


def edit_image(api_key: str, image_path: str, prompt: str, size: str = DEFAULT_SIZE) -> bytes:
    client = openai.OpenAI(api_key=api_key)
    png_bytes = _prepare_png_for_edit(image_path)
    image_file = io.BytesIO(png_bytes)
    image_file.name = "reference.png"
    response = client.images.edit(
        model=MODEL,
        image=image_file,
        prompt=prompt,
        n=1,
        size=size,
    )
    return base64.b64decode(response.data[0].b64_json)

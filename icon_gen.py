"""Generator ikon — AI image + rembg + resize."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image
from rembg import remove  # type: ignore[import-untyped]

from models import ApiUsage, Config, GenerationResult
from providers import ImageProvider

logger = logging.getLogger(__name__)


async def generate_icon(
    prompt: str,
    label: str,
    config: Config,
    output_path: Path,
    provider: ImageProvider,
    model: str,
) -> GenerationResult | None:
    """Generuj ikone: AI image -> rembg -> autocrop -> resize. None przy bledzie."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    original_dir = output_path.parent / "original"

    raw_bytes, usage = await provider.generate_image(
        prompt, model, config.max_retries, config.timeout_image,
    )
    if not raw_bytes:
        return None

    img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")

    # Zapisz oryginal (opcjonalnie)
    if config.keep_originals:
        original_dir.mkdir(parents=True, exist_ok=True)
        orig_path = original_dir / output_path.name
        img.save(str(orig_path), "PNG")

    # rembg
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    removed = remove(buf.read())
    img = Image.open(io.BytesIO(removed)).convert("RGBA")

    # Autocrop
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Pad + square
    pad = 2
    w, h = img.size
    side = max(w, h) + pad * 2
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - w) // 2, (side - h) // 2), img)

    # Resize
    icon_size = config.icon_size
    final = square.resize((icon_size, icon_size), Image.BICUBIC)  # type: ignore[attr-defined]
    final.save(str(output_path), "PNG")

    return GenerationResult(
        icon_path=str(output_path),
        original_path=str(original_dir / output_path.name) if config.keep_originals else "",
        element_name=label,
        prompt=prompt,
        usage=usage,
    )

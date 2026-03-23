"""Composer — ikona + tekst domeny = logo .webp."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from models import ColorPalette, Config

logger = logging.getLogger(__name__)


def compose_logos(
    icon_paths: list[Path],
    text: str,
    palette: ColorPalette,
    config: Config,
    output_dir: Path,
) -> list[Path]:
    """Dla kazdej ikony tworzy logo w kazdym rozmiarze."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []

    for i, icon_path in enumerate(icon_paths):
        icon = Image.open(str(icon_path)).convert("RGBA")
        for height in config.logo_sizes:
            font = _load_font(config, height)
            path = output_dir / f"logo_v{i + 1}_{height}.webp"
            logo = _compose(icon, text, palette.primary, height, font, config.icon_text_gap)
            logo.save(str(path), "WEBP", lossless=True)
            results.append(path)

    return results


def _compose(
    icon: Image.Image,
    text: str,
    color: str,
    height: int,
    font: ImageFont.FreeTypeFont,
    gap: int,
) -> Image.Image:
    """Sklada jedno logo: ikona + tekst."""
    icon_resized = icon.resize((height, height), Image.BICUBIC)  # type: ignore[attr-defined]

    # Zmierz tekst
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = tmp.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    canvas = Image.new("RGBA", (height + gap + tw, height), (0, 0, 0, 0))
    canvas.paste(icon_resized, (0, 0), icon_resized)

    draw = ImageDraw.Draw(canvas)
    ty = (height - th) // 2 - bbox[1]
    draw.text((height + gap, ty), text, fill=color, font=font)

    return canvas


def _load_font(config: Config, height: int) -> ImageFont.FreeTypeFont:
    size = max(config.font_size_min, int(height * config.font_multiplier))
    path = Path(config.font_path)
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except OSError:
        return ImageFont.load_default()  # type: ignore[return-value]

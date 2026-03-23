"""Modele danych i konfiguracja."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


# --- Typy danych ---


class DomainInfo(BaseModel):
    domain: str
    keywords: list[str] = []
    icon_hint: str = ""
    display_name: str = ""
    city_name: str = ""


class ColorPalette(BaseModel):
    primary: str = "#CC2233"
    accent: str = "#1A3A6A"


class SuggestedColors(BaseModel):
    primary: str
    accent: str
    reasoning: str = ""


class ApiUsage(BaseModel):
    model: str
    total_cost_usd: float = 0.0
    duration_s: float = 0.0


class GenerationResult(BaseModel):
    icon_path: str
    original_path: str = ""
    element_name: str
    prompt: str = ""
    usage: ApiUsage


# --- Konfiguracja ---


class Config(BaseModel):
    provider: str = "google"
    google_api_key_env: str = "GOOGLE_API_KEY"
    openrouter_api_key_env: str = "OPENROUTER_API_KEY"
    image_model: str = "gemini-3-pro-image-preview"
    text_model: str = "gemini-2.5-flash"
    timeout_image: float = 120.0
    timeout_text: float = 30.0
    max_retries: int = 3
    keep_originals: bool = False
    keep_last_runs: int = 3
    icon_size: int = 64
    logo_sizes: list[int] = [64, 32]
    font_path: str = "assets/fonts/Poppins-Bold.ttf"
    font_multiplier: float = 0.55
    font_size_min: int = 12
    icon_text_gap: int = 6
    output_dir: str = "output"
    default_primary: str = "#CC2233"
    default_accent: str = "#1A3A6A"
    negative: str = (
        "no text, no thin lines, no shadows, no gradients, "
        "no 3D, no internal cutouts, no multiple objects"
    )

    @property
    def google_api_key(self) -> str:
        load_dotenv()
        key = os.getenv(self.google_api_key_env, "")
        if not key:
            raise RuntimeError(f"Brak {self.google_api_key_env} w .env")
        return key

    @property
    def openrouter_api_key(self) -> str:
        load_dotenv()
        key = os.getenv(self.openrouter_api_key_env, "")
        if not key:
            raise RuntimeError(f"Brak {self.openrouter_api_key_env} w .env")
        return key


def load_config(path: str | Path = "config.yaml") -> Config:
    """Zaladuj config z YAML."""
    load_dotenv()
    p = Path(path)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return Config(**data)
    return Config()

"""Providery: Google Gemini direct + OpenRouter proxy."""

from __future__ import annotations

import abc
import base64
import logging
import time

import httpx

from models import ApiUsage, Config

logger = logging.getLogger(__name__)

# Szacunkowy koszt per obraz
_COST: dict[str, float] = {
    "gemini-2.5-flash-image": 0.003,
    "gemini-3-pro-image-preview": 0.07,
    "google/gemini-3.1-flash-image-preview": 0.01,
    "google/gemini-2.5-flash-image-preview": 0.003,
    "openai/gpt-5-image-mini": 0.02,
    "openai/gpt-5-image": 0.07,
}


def estimate_cost(model: str) -> float:
    if model in _COST:
        return _COST[model]
    for k, v in _COST.items():
        if k in model or model in k:
            return v
    return 0.0


class ImageProvider(abc.ABC):
    """Baza dla providerow image-gen."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @abc.abstractmethod
    async def generate_image(
        self, prompt: str, model: str, max_retries: int, timeout: float,
    ) -> tuple[bytes | None, ApiUsage]: ...


class GoogleProvider(ImageProvider):
    """Google Gemini Image API — bezposrednio."""

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate_image(
        self, prompt: str, model: str, max_retries: int = 3, timeout: float = 120.0,
    ) -> tuple[bytes | None, ApiUsage]:
        t0 = time.monotonic()
        sq_prompt = prompt + " Square 1:1 image."

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        f"{self.API_BASE}/{model}:generateContent?key={self.api_key}",
                        json={
                            "contents": [{"parts": [{"text": sq_prompt}]}],
                            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                usage = ApiUsage(
                    model=model,
                    duration_s=round(time.monotonic() - t0, 2),
                    total_cost_usd=estimate_cost(model),
                )
                candidates = data.get("candidates", [])
                if not candidates:
                    logger.warning("Google %s proba %d/%d: brak candidates", model, attempt, max_retries)
                    continue
                for part in candidates[0].get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        return base64.b64decode(part["inlineData"]["data"]), usage
                logger.warning("Google %s proba %d/%d: brak obrazu", model, attempt, max_retries)
            except httpx.HTTPStatusError as e:
                logger.warning("Google %s proba %d/%d: HTTP %d", model, attempt, max_retries, e.response.status_code)
            except (httpx.ReadTimeout, KeyError) as e:
                logger.warning("Google %s proba %d/%d: %s", model, attempt, max_retries, e)

        return None, ApiUsage(model=model, duration_s=round(time.monotonic() - t0, 2))


class OpenRouterProvider(ImageProvider):
    """OpenRouter API — proxy do Gemini, OpenAI, itp."""

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    async def generate_image(
        self, prompt: str, model: str, max_retries: int = 3, timeout: float = 120.0,
    ) -> tuple[bytes | None, ApiUsage]:
        t0 = time.monotonic()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image"],
            "image_config": {"aspect_ratio": "1:1", "image_size": "1K"},
        }

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(self.API_URL, json=body, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

                usage = ApiUsage(
                    model=model,
                    duration_s=round(time.monotonic() - t0, 2),
                    total_cost_usd=estimate_cost(model),
                )
                choices = data.get("choices", [])
                if not choices:
                    continue
                msg = choices[0].get("message", {})
                images = msg.get("images", [])
                if not images:
                    continue
                url = images[0]["image_url"]["url"]
                b64 = url.split(";base64,", 1)[1] if ";base64," in url else url
                return base64.b64decode(b64), usage
            except httpx.HTTPStatusError as e:
                logger.warning("OpenRouter %s proba %d/%d: HTTP %d", model, attempt, max_retries, e.response.status_code)
            except (httpx.ReadTimeout, KeyError) as e:
                logger.warning("OpenRouter %s proba %d/%d: %s", model, attempt, max_retries, e)

        return None, ApiUsage(model=model, duration_s=round(time.monotonic() - t0, 2))


def get_provider(config: Config) -> ImageProvider:
    """Zwroc provider na podstawie config."""
    if config.provider == "openrouter":
        return OpenRouterProvider(config.openrouter_api_key)
    return GoogleProvider(config.google_api_key)


async def google_text_chat(
    api_key: str, model: str, prompt: str, timeout: float = 30.0,
) -> str:
    """Google Gemini text API — zwraca tekst odpowiedzi."""
    url = f"{GoogleProvider.API_BASE}/{model}:generateContent?key={api_key}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["TEXT"]},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "text" in part:
            return part["text"]  # type: ignore[no-any-return]
    raise RuntimeError("Google: brak tekstu w odpowiedzi")

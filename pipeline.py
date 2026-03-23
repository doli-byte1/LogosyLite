"""Pipeline — glowny flow auto-mode."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from cleanup import cleanup_output
from composer import compose_logos
from domain_parser import enhance_domain_info, parse_domain
from history import get_used_labels, save_prompts
from icon_gen import generate_icon
from models import ColorPalette, Config, GenerationResult, SuggestedColors, load_config
from providers import estimate_cost, get_provider, google_text_chat

logger = logging.getLogger(__name__)


def _load_prompt_file(name: str) -> str:
    path = Path(__file__).parent / "prompts" / name
    return path.read_text(encoding="utf-8")


def _resolve_colors(
    color1: str | None,
    color2: str | None,
    suggested: SuggestedColors | None,
    config: Config,
) -> ColorPalette:
    primary = color1 or (suggested.primary if suggested else None) or config.default_primary
    accent = color2 or (suggested.accent if suggested else None) or config.default_accent
    return ColorPalette(primary=primary, accent=accent)


async def _generate_prompts(
    miasto: str,
    domain: str,
    primary: str,
    accent: str,
    config: Config,
    used_labels: list[str],
) -> tuple[list[dict[str, str]], dict[str, str] | None]:
    """AI generuje 4 prompty do image-gen + kolory."""
    meta_template = _load_prompt_file("meta_prompt.txt")
    image_template = _load_prompt_file("image_template.txt")

    history_block = ""
    if used_labels:
        items = "\n".join(f"- {l}" for l in used_labels)
        history_block = (
            f"Wczesniej wygenerowano juz ikony z tymi motywami (NIE POWTARZAJ):\n{items}"
        )

    meta = meta_template.format(
        miasto=miasto,
        domain=domain,
        primary=primary,
        accent=accent,
        negative=config.negative,
        image_template=image_template,
        history_block=history_block,
    )

    raw = await google_text_chat(
        api_key=config.google_api_key,
        model=config.text_model,
        prompt=meta,
        timeout=config.timeout_text,
    )

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"Brak JSON w odpowiedzi AI: {raw[:200]}")

    data = json.loads(raw[start:end])
    prompts: list[dict[str, str]] = data.get("prompts", [])
    colors: dict[str, str] | None = data.get("colors")

    if not prompts:
        raise ValueError("AI nie zwrocilo promptow")
    return prompts, colors


async def auto_generate(
    domain: str,
    model_override: str | None = None,
    color1: str | None = None,
    color2: str | None = None,
    config_path: str = "config.yaml",
) -> dict:
    """Pelny auto pipeline. Zwraca dict z wynikami."""
    t0 = time.monotonic()
    config = load_config(config_path)

    # 1. Parse domain
    domain_info = parse_domain(domain)
    miasto = domain_info.city_name or ""
    if not miasto:
        raise ValueError(f"Nie wykryto miasta z domeny '{domain}'")

    domain_info = enhance_domain_info(domain_info, miasto)
    display = domain_info.display_name or domain
    logger.info("Auto: %s -> %s (%s)", domain, miasto, display)

    # 2. Model + provider
    model = model_override or config.image_model
    provider = get_provider(config)
    est = estimate_cost(model)
    logger.info("Model: %s (~$%.3f/obraz), provider: %s", model, est, config.provider)

    # 3. Historia — co juz bylo
    output_dir = Path(config.output_dir)
    used_labels = get_used_labels(output_dir, domain)
    if used_labels:
        logger.info("Historia: %d uzytych motywow", len(used_labels))

    # 4. AI generuje 4 prompty + kolory
    logger.info("Generowanie promptow (AI text)...")
    ai_prompts, ai_colors = await _generate_prompts(
        miasto, domain, config.default_primary, config.default_accent,
        config, used_labels,
    )

    for i, p in enumerate(ai_prompts[:4], 1):
        logger.info("  [%d] %s", i, p.get("label", "?"))

    # 5. Kolory
    suggested = None
    if ai_colors and "primary" in ai_colors:
        suggested = SuggestedColors(
            primary=ai_colors["primary"],
            accent=ai_colors.get("accent", ai_colors["primary"]),
            reasoning=ai_colors.get("reasoning", "auto"),
        )
    palette = _resolve_colors(color1, color2, suggested, config)

    # 6. Generowanie ikon
    model_short = model.split("/")[-1]
    model_dir = output_dir / domain / model_short
    model_dir.mkdir(parents=True, exist_ok=True)

    gen_results: list[GenerationResult] = []
    for i, prompt_data in enumerate(ai_prompts[:4], 1):
        label = prompt_data.get("label", f"prompt_{i}")
        prompt_text = prompt_data.get("prompt", "")
        if not prompt_text:
            continue
        logger.info("  [%d/4] %s ...", i, label)
        r = await generate_icon(
            prompt_text, label, config,
            model_dir / f"icon_v{i}.png",
            provider, model,
        )
        if r:
            gen_results.append(r)
            logger.info("    OK (%.1fs)", r.usage.duration_s)
        else:
            logger.warning("    FAIL")

    if not gen_results:
        raise RuntimeError("Zadna ikona sie nie wygenerowala")

    # 7. Compose logo
    icon_paths = [Path(r.icon_path) for r in gen_results]
    logo_paths = compose_logos(icon_paths, display, palette, config, model_dir)
    logger.info("%d logo z domena", len(logo_paths))

    city_dir = model_dir / "miasto"
    city_logos = compose_logos(icon_paths, miasto, palette, config, city_dir)
    logo_paths.extend(city_logos)
    logger.info("%d logo z miastem", len(city_logos))

    # 8. Historia — zapisz nowe prompty
    save_prompts(output_dir, domain, ai_prompts[:4])

    # 9. Cleanup
    removed = cleanup_output(domain, config)
    if removed:
        logger.info("Cleanup: usunieto %d starych runow", removed)

    # 10. Metadata
    gen_cost = sum(r.usage.total_cost_usd for r in gen_results)
    elapsed = time.monotonic() - t0

    result = {
        "status": "done",
        "miasto": miasto,
        "domain": domain,
        "display_name": display,
        "model": model,
        "provider": config.provider,
        "colors": palette.model_dump(),
        "icons": [r.icon_path for r in gen_results],
        "logos": [str(p) for p in logo_paths],
        "ai_prompts": [p.get("label", "") for p in ai_prompts[:4]],
        "cost_usd": round(gen_cost + 0.001, 4),
        "duration_s": round(elapsed, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }

    meta_path = output_dir / domain / "metadata.json"
    meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Gotowe: %d ikon, %d logo, $%.4f, %.0fs", len(gen_results), len(logo_paths), gen_cost, elapsed)
    return result

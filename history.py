"""Historia promptow — nie powtarzaj tych samych ikon."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

MAX_HISTORY = 10


def _history_path(output_dir: Path, domain: str) -> Path:
    return output_dir / domain / "history.json"


def load_history(output_dir: Path, domain: str) -> list[dict[str, str]]:
    """Zaladuj historie promptow dla domeny."""
    path = _history_path(output_dir, domain)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("prompts", [])[-MAX_HISTORY:]
    return []


def get_used_labels(output_dir: Path, domain: str) -> list[str]:
    """Zwroc labelki juz uzytych promptow."""
    return [p.get("label", "") for p in load_history(output_dir, domain) if p.get("label")]


def save_prompts(output_dir: Path, domain: str, prompts: list[dict[str, str]]) -> None:
    """Dodaj prompty do historii (max 10)."""
    path = _history_path(output_dir, domain)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = load_history(output_dir, domain)
    ts = datetime.now(UTC).isoformat()
    for p in prompts:
        existing.append({
            "timestamp": ts,
            "label": p.get("label", ""),
            "prompt": p.get("prompt", ""),
        })

    # Trzymaj max 10
    existing = existing[-MAX_HISTORY:]
    path.write_text(
        json.dumps({"prompts": existing}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

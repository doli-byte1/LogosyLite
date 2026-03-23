"""Cleanup — usuwanie starych runow i oryginatow."""

from __future__ import annotations

import shutil
from pathlib import Path

from models import Config


def cleanup_output(domain: str, config: Config) -> int:
    """Usun stare runy. Zwraca ile usunietych."""
    output_dir = Path(config.output_dir) / domain
    if not output_dir.exists():
        return 0

    keep = config.keep_last_runs
    if keep <= 0:
        return 0

    # Znajdz podkatalogi z runami (po dacie modyfikacji)
    run_dirs = sorted(
        (d for d in output_dir.iterdir() if d.is_dir() and d.name != "original"),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    removed = 0
    for d in run_dirs[keep:]:
        shutil.rmtree(d)
        removed += 1

    return removed

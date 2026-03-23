"""Parser domen — wykrywanie miasta z nazwy domeny."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from models import DomainInfo

_FALLBACK_WORDS = [
    "gazeta", "portal", "kurier", "info", "sport", "dziennik", "radio",
    "wiadomosci", "news", "express", "tygodnik", "nasz", "moj", "moja",
    "tylko", "super", "extra", "24", "365",
]
_FALLBACK_HINTS = {"gazeta": "newspaper", "portal": "web portal", "radio": "radio wave"}


@lru_cache(maxsize=1)
def _load_keywords() -> tuple[list[str], dict[str, str]]:
    path = Path(__file__).parent / "assets" / "domain_keywords.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("known_words", _FALLBACK_WORDS), data.get("icon_hints", _FALLBACK_HINTS)
    return _FALLBACK_WORDS, _FALLBACK_HINTS


@lru_cache(maxsize=1)
def _load_city_db() -> dict[str, str]:
    path = Path(__file__).parent / "assets" / "city_adjectives.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    return {}


def _detect_city(domain_name: str, found_keywords: list[str]) -> str | None:
    db = _load_city_db()
    if not db:
        return None
    # Pelna nazwa
    if domain_name in db:
        return db[domain_name]
    # Po usunieciu keywords
    remaining = domain_name
    for kw in found_keywords:
        remaining = remaining.replace(kw, "")
    remaining = re.sub(r"\d+", "", remaining).strip()
    if remaining and remaining in db:
        return db[remaining]
    # Najdluzszy substring
    best, best_len = None, 0
    for key, city in db.items():
        if key in domain_name and len(key) > best_len:
            best, best_len = city, len(key)
    return best


def parse_domain(domain: str) -> DomainInfo:
    """Parsuj domene — wyciagnij miasto, keywords, display_name."""
    parts = domain.split(".")
    name = parts[0].lower()
    tld = ".".join(parts[1:]) if len(parts) > 1 else "pl"

    known_words, icon_hints = _load_keywords()
    found: list[str] = [w for w in known_words if w in name]
    keywords = [p for p in re.split(r"[\d\-_]+", name) if len(p) > 2]

    hint = ""
    for kw in found:
        if kw in icon_hints:
            hint = icon_hints[kw]
            break
    if not hint and name:
        hint = f"stylized letter {name[0].upper()}"

    city = _detect_city(name, found)

    # CamelCase display
    display = name
    if display:
        display = display[0].upper() + display[1:]

    return DomainInfo(
        domain=domain,
        keywords=keywords,
        icon_hint=hint,
        display_name=f"{display}.{tld}",
        city_name=city or "",
    )


def enhance_domain_info(info: DomainInfo, miasto: str) -> DomainInfo:
    """Popraw display_name i icon_hint na podstawie miasta."""
    city_parts = miasto.split()
    domain_base = info.domain.split(".")[0].lower()

    display = domain_base
    for part in sorted(city_parts, key=len, reverse=True):
        ascii_part = (
            part.lower()
            .replace("\u0105", "a").replace("\u0107", "c").replace("\u0119", "e")
            .replace("\u0142", "l").replace("\u0144", "n").replace("\u00f3", "o")
            .replace("\u015b", "s").replace("\u017a", "z").replace("\u017c", "z")
        )
        if ascii_part in display:
            display = display.replace(ascii_part, ascii_part.capitalize(), 1)

    if display == domain_base:
        display = domain_base.capitalize()
    elif display[0].islower():
        display = display[0].upper() + display[1:]

    tld = ".".join(info.domain.split(".")[1:])
    info.display_name = f"{display}.{tld}"

    if len(city_parts) >= 2 and info.icon_hint.startswith("stylized letter "):
        initials = "".join(p[0].upper() for p in city_parts if p)
        info.icon_hint = f"stylized letters {initials}"

    return info

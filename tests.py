"""Testy LogosyLite — uruchom: python tests.py

Testuje kolejno:
1. Import modulow
2. Parsowanie domeny
3. Historia promptow
4. Config
5. CLI (dry run)
6. API — POST /generate (async)
7. API — GET /status/{id}
8. API — GET /jobs
9. API — GET /file (pobranie logo)
10. API — POST /generate (sync) + zapis plikow

Wymaga: pip install -r requirements.txt + .env z GOOGLE_API_KEY
Testy 6-10 wymagaja uruchomionego serwera: uvicorn app:app --port 8000
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# ---------- Helpers ----------

_passed = 0
_failed = 0


def _ok(name: str, detail: str = "") -> None:
    global _passed
    _passed += 1
    print(f"  [OK] {name}" + (f" — {detail}" if detail else ""))


def _fail(name: str, err: str) -> None:
    global _failed
    _failed += 1
    print(f"  [FAIL] {name} — {err}")


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ---------- 1. Import modulow ----------

def test_imports() -> None:
    _section("1. Import modulow")
    modules = [
        "models", "providers", "domain_parser", "history",
        "icon_gen", "composer", "cleanup", "pipeline",
    ]
    for m in modules:
        try:
            __import__(m)
            _ok(f"import {m}")
        except Exception as e:
            _fail(f"import {m}", str(e))


# ---------- 2. Parsowanie domeny ----------

def test_domain_parser() -> None:
    _section("2. Parsowanie domeny")
    from domain_parser import enhance_domain_info, parse_domain

    cases = [
        ("srodawielkopolska24.pl", "Środa Wielkopolska"),
        ("gazetakrakowska.pl", "Kraków"),
        ("tylkotarnowskiegory.pl", "Tarnowskie Góry"),
    ]
    for domain, expected_city in cases:
        info = parse_domain(domain)
        if info.city_name == expected_city:
            _ok(f"parse_domain({domain})", f"miasto={info.city_name}")
        else:
            _fail(f"parse_domain({domain})", f"oczekiwano '{expected_city}', got '{info.city_name}'")

    # enhance
    info = parse_domain("tylkotarnowskiegory.pl")
    info = enhance_domain_info(info, "Tarnowskie Góry")
    if ".pl" in info.display_name:
        _ok("enhance_domain_info", f"display={info.display_name}")
    else:
        _fail("enhance_domain_info", f"brak .pl w display: {info.display_name}")


# ---------- 3. Historia ----------

def test_history() -> None:
    _section("3. Historia promptow")
    from history import get_used_labels, save_prompts

    test_dir = Path("output")
    test_domain = "_test_history_"

    # Zapisz
    save_prompts(test_dir, test_domain, [
        {"label": "Ratusz", "prompt": "test1"},
        {"label": "Kosciol", "prompt": "test2"},
    ])
    labels = get_used_labels(test_dir, test_domain)
    if "Ratusz" in labels and "Kosciol" in labels:
        _ok("save + load", f"labels={labels}")
    else:
        _fail("save + load", f"brak oczekiwanych labeli: {labels}")

    # Cleanup
    hist_path = test_dir / test_domain / "history.json"
    if hist_path.exists():
        hist_path.unlink()
        (test_dir / test_domain).rmdir()


# ---------- 4. Config ----------

def test_config() -> None:
    _section("4. Config")
    from models import load_config

    config = load_config()
    if config.image_model:
        _ok("load_config", f"model={config.image_model}, provider={config.provider}")
    else:
        _fail("load_config", "brak image_model")

    try:
        _ = config.google_api_key
        _ok("google_api_key", "klucz dostepny")
    except RuntimeError as e:
        _fail("google_api_key", str(e))


# ---------- 5. CLI dry run ----------

def test_cli_help() -> None:
    _section("5. CLI")
    import subprocess

    result = subprocess.run(
        [sys.executable, "cli.py", "--help"],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and "domain" in result.stdout.lower():
        _ok("cli.py --help", "dziala")
    else:
        _fail("cli.py --help", result.stderr[:100])


# ---------- 6-10. Testy API (wymagaja serwera) ----------

def test_api() -> None:
    """Testy API — wymaga: uvicorn app:app --port 8000"""
    try:
        import httpx
    except ImportError:
        _fail("httpx import", "pip install httpx")
        return

    BASE = "http://localhost:8000"

    # Sprawdz czy serwer dziala
    try:
        r = httpx.get(f"{BASE}/jobs", timeout=3)
        r.raise_for_status()
    except Exception:
        print("  [SKIP] Serwer nie dziala na localhost:8000")
        print("  Uruchom: uvicorn app:app --port 8000")
        return

    # 6. POST /generate (async)
    _section("6. POST /generate (async)")
    test_domain = "srodawielkopolska24.pl"
    r = httpx.post(f"{BASE}/generate", json={"domain": test_domain}, timeout=10)
    if r.status_code == 200 and "job_id" in r.json():
        job_id = r.json()["job_id"]
        _ok("POST /generate", f"job_id={job_id}")
    else:
        _fail("POST /generate", f"status={r.status_code}")
        return

    # 7. GET /status/{id}
    _section("7. GET /status/{job_id}")
    # Czekaj na zakonczenie (max 5 min)
    for _ in range(60):
        r = httpx.get(f"{BASE}/status/{job_id}", timeout=5)
        data = r.json()
        status = data.get("status", "")
        if status == "done":
            _ok("GET /status", f"done, ikony={len(data.get('icons', []))}")
            break
        if status == "error":
            _fail("GET /status", f"error: {data.get('error', '?')}")
            break
        time.sleep(5)
    else:
        _fail("GET /status", "timeout 5min")
        return

    # 8. GET /jobs
    _section("8. GET /jobs")
    r = httpx.get(f"{BASE}/jobs", timeout=5)
    jobs = r.json()
    if isinstance(jobs, list) and len(jobs) > 0:
        _ok("GET /jobs", f"{len(jobs)} jobow")
    else:
        _fail("GET /jobs", "pusta lista")

    # 9. GET /file (pobranie logo)
    _section("9. GET /file (pobranie logo)")
    logos = data.get("logos", [])
    if logos:
        # Wyciagnij sciezke wzgledna z output/{domain}/...
        logo_path = logos[0]
        # Usun prefix output/ jesli jest
        rel = logo_path.replace("output/", "").replace("output\\", "")
        parts = rel.split("/", 1) if "/" in rel else rel.split("\\", 1)
        if len(parts) == 2:
            domain_part, file_part = parts
            r = httpx.get(f"{BASE}/file/{domain_part}/{file_part}", timeout=10)
            if r.status_code == 200 and len(r.content) > 100:
                # Zapisz lokalnie
                save_path = Path(f"_test_logo.webp")
                save_path.write_bytes(r.content)
                _ok("GET /file", f"pobrano {len(r.content)} bytes -> {save_path}")
                save_path.unlink()
            else:
                _fail("GET /file", f"status={r.status_code}, size={len(r.content)}")
        else:
            _fail("GET /file", f"nie mozna sparsowac sciezki: {logo_path}")
    else:
        _fail("GET /file", "brak logo w wynikach")

    # 10. POST /generate (sync) + zapis
    _section("10. POST /generate (sync) + zapis plikow")
    r = httpx.post(
        f"{BASE}/generate",
        json={"domain": test_domain, "sync": True},
        timeout=600,
    )
    if r.status_code == 200:
        result = r.json()
        _ok("POST /generate sync", f"status={result.get('status')}")

        # Zapisz wszystkie logo
        save_dir = Path("_test_output")
        save_dir.mkdir(exist_ok=True)
        saved = 0
        for logo in result.get("logos", []):
            rel = logo.replace("output/", "").replace("output\\", "")
            parts = rel.split("/", 1) if "/" in rel else rel.split("\\", 1)
            if len(parts) == 2:
                r2 = httpx.get(f"{BASE}/file/{parts[0]}/{parts[1]}", timeout=10)
                if r2.status_code == 200:
                    fname = Path(parts[1]).name
                    (save_dir / fname).write_bytes(r2.content)
                    saved += 1

        if saved > 0:
            _ok("Zapis plikow", f"{saved} logo zapisanych w {save_dir}/")
            # Cleanup
            for f in save_dir.iterdir():
                f.unlink()
            save_dir.rmdir()
        else:
            _fail("Zapis plikow", "zero plikow zapisanych")
    else:
        _fail("POST /generate sync", f"status={r.status_code}: {r.text[:100]}")


# ---------- Main ----------

def main() -> None:
    print("=" * 60)
    print("  LogosyLite — testy")
    print("=" * 60)

    test_imports()
    test_domain_parser()
    test_history()
    test_config()
    test_cli_help()
    test_api()

    print(f"\n{'=' * 60}")
    print(f"  WYNIK: {_passed} passed, {_failed} failed")
    print(f"{'=' * 60}")
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()

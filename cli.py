"""CLI — python cli.py srodawielkopolska24.pl"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from pipeline import auto_generate


def main() -> None:
    parser = argparse.ArgumentParser(description="LogosyLite — auto logo generator")
    parser.add_argument("domain", help="Domena (np. srodawielkopolska24.pl)")
    parser.add_argument("--model", default=None, help="Model image-gen (override config)")
    parser.add_argument("--color1", default=None, help="Kolor glowny (hex)")
    parser.add_argument("--color2", default=None, help="Kolor akcentowy (hex)")
    parser.add_argument("--config", default="config.yaml", help="Sciezka do config")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        result = asyncio.run(auto_generate(
            domain=args.domain,
            model_override=args.model,
            color1=args.color1,
            color2=args.color2,
            config_path=args.config,
        ))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError) as e:
        print(f"BLAD: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

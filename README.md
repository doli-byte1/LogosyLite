# LogosyLite

Automatyczny generator logo dla polskich portali miejskich.
Podaj domenę — AI wygeneruje ikonę i złoży gotowe logo.

**Jak to działa:** domena → wykrycie miasta (baza 940 miast) → AI generuje prompt → ikona (Gemini image) → usunięcie tła → kompozycja logo z tekstem domeny.

## Wymagania

- Python 3.11+
- Klucz API: [Google AI Studio](https://aistudio.google.com/apikey) (darmowy)

## Szybki start

```bash
# 1. Sklonuj repo
git clone https://github.com/doli-byte1/LogosyLite.git
cd LogosyLite

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Skonfiguruj klucz API
cp .env.example .env
# Wpisz swój GOOGLE_API_KEY w pliku .env

# 4. Generuj logo
python cli.py srodawielkopolska24.pl
```

## CLI

```bash
python cli.py srodawielkopolska24.pl
python cli.py moja-jeleniagora.pl --model gemini-2.5-flash-image
python cli.py gazetakrakowska.pl --color1 "#006400" --color2 "#FFD700"
python cli.py srodawielkopolska24.pl -v   # debug
```

## API

```bash
# Uruchom serwer
uvicorn app:app --host 0.0.0.0 --port 8000

# Async (domyślny) — startuje job w tle
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"domain": "srodawielkopolska24.pl"}'
# -> {"job_id": "abc123", "status": "running"}

# Sprawdź status
curl http://localhost:8000/status/abc123
# -> {"status": "done", "icon": "...", "logo": "...", ...}

# Sync — czeka na wynik
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"domain": "srodawielkopolska24.pl", "sync": true}'

# Lista jobów
curl http://localhost:8000/jobs

# Pobierz plik
curl http://localhost:8000/file/srodawielkopolska24.pl/gemini-2.5-flash-image/logo_v1_64.webp -o logo.webp
```

### Response (sync / status done)

```json
{
  "status": "done",
  "miasto": "Środa Wielkopolska",
  "domain": "srodawielkopolska24.pl",
  "display_name": "SrodaWielkopolska24.pl",
  "model": "gemini-2.5-flash-image",
  "colors": {"primary": "#C41E3A", "accent": "#1A3A6A"},
  "icon": "output/srodawielkopolska24.pl/gemini-2.5-flash-image/icon.png",
  "logo": "output/srodawielkopolska24.pl/gemini-2.5-flash-image/logo_v1_64.webp",
  "label": "Litera S z kolegiata",
  "cost_usd": 0.004,
  "duration_s": 12.3
}
```

## Konfiguracja

`config.yaml` — wszystkie ustawienia:

| Klucz | Domyślna | Opis |
|-------|----------|------|
| `provider` | `google` | `google` (direct) lub `openrouter` (proxy) |
| `image_model` | `gemini-2.5-flash-image` | Model do generowania ikon |
| `text_model` | `gemini-2.5-flash` | Model do generowania promptów |
| `keep_originals` | `false` | Trzymaj oryginały AI (przed rembg) |
| `keep_last_runs` | `3` | Ile ostatnich runów per domena |
| `icon_size` | `64` | Rozmiar ikony (px) |
| `logo_sizes` | `[64]` | Rozmiary logo (wysokość px) |

## Prompty

Edytowalne pliki w `prompts/`:
- `meta_prompt.txt` — prompt do AI który generuje prompt do ikony
- `image_template.txt` — szablon prompta do generowania obrazu

## Jak to działa

```
domena → wykryj miasto (940 miast w bazie)
  → AI generuje prompt (Gemini text)
  → 1 ikona (Gemini image)
  → rembg → autocrop → resize 64px
  → compose: ikona + tekst domeny = logo .webp
```

Historia 10 ostatnich promptów — AI nie powtarza tych samych motywów.

## Struktura plików

```
LogosyLite/
├── app.py              # FastAPI
├── cli.py              # CLI
├── pipeline.py         # główny flow
├── providers.py        # Google + OpenRouter
├── icon_gen.py         # rembg + resize
├── composer.py         # ikona + tekst
├── cleanup.py          # czyszczenie starych runów
├── domain_parser.py    # wykrywanie miasta z domeny
├── models.py           # typy + config
├── history.py          # historia promptów
├── prompts/            # pliki promptów (edytowalne)
├── assets/             # font + baza miast
├── config.yaml         # konfiguracja
└── .env                # klucze API (nie w repo)
```

## Koszt

~$0.004 per run (1 ikona, gemini-2.5-flash-image).

## Licencja

MIT — zobacz [LICENSE](LICENSE).

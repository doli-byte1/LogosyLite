# LogosyLite

Generator logo dla polskich portali miejskich. Podaj domene — dostaniesz logo.

## Szybki start

```bash
# 1. Zainstaluj
pip install -r requirements.txt

# 2. Klucz API
cp .env.example .env
# Wpisz GOOGLE_API_KEY w .env

# 3. CLI
python cli.py srodawielkopolska24.pl

# 4. API
uvicorn app:app --host 0.0.0.0 --port 8000
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
# Async (domyslny) — startuje job w tle
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"domain": "srodawielkopolska24.pl"}'
# -> {"job_id": "abc123", "status": "running"}

# Sprawdz status
curl http://localhost:8000/status/abc123

# Sync — czeka na wynik
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"domain": "srodawielkopolska24.pl", "sync": true}'

# Lista jobow
curl http://localhost:8000/jobs

# Pobierz plik
curl http://localhost:8000/file/srodawielkopolska24.pl/gemini-3-pro-image-preview/logo_v1_64.webp -o logo.webp
```

## Konfiguracja

`config.yaml` — wszystkie ustawienia:

| Klucz | Domyslna | Opis |
|-------|----------|------|
| `provider` | `google` | `google` (direct) lub `openrouter` (proxy) |
| `image_model` | `gemini-3-pro-image-preview` | Model do generowania ikon |
| `text_model` | `gemini-2.5-flash` | Model do generowania promptow |
| `keep_originals` | `false` | Trzymaj oryginaly AI (przed rembg) |
| `keep_last_runs` | `3` | Ile ostatnich runow per domena |
| `icon_size` | `64` | Rozmiar ikony (px) |
| `logo_sizes` | `[64, 32]` | Rozmiary logo (wysokosc px) |

## Prompty

Edytowalne pliki w `prompts/`:
- `meta_prompt.txt` — prompt do AI ktory generuje 4 prompty do ikon
- `image_template.txt` — szablon prompta do generowania obrazow

## Jak to dziala

```
domena → wykryj miasto (940 miast w bazie)
  → AI generuje 4 prompty (Gemini text)
  → 4 ikony (Gemini image)
  → rembg → autocrop → resize 64px
  → compose: ikona + tekst domeny = logo .webp
  → compose: ikona + nazwa miasta = logo .webp
```

Historia 10 ostatnich promptow — AI nie powtarza tych samych motywow.

## Pliki

```
LogosyLite/
├── app.py              # FastAPI
├── cli.py              # CLI
├── pipeline.py         # glowny flow
├── providers.py        # Google + OpenRouter
├── icon_gen.py         # rembg + resize
├── composer.py         # ikona + tekst
├── cleanup.py          # czyszczenie
├── domain_parser.py    # wykrywanie miasta
├── models.py           # typy + config
├── history.py          # historia promptow
├── prompts/            # pliki promptow (edytowalne)
├── assets/             # font + baza miast
├── config.yaml         # konfiguracja
└── .env                # klucze API
```

## Koszt

~$0.28 per run (4 ikony gemini-3-pro-image-preview).
Z gemini-2.5-flash-image: ~$0.012 per run.

# LogosyLite — jak to dziala

## Ogolny flow

```
                         INPUT
                           │
                     ┌─────┴─────┐
                     │  domena   │
                     │  (string) │
                     └─────┬─────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
     CLI (cli.py)    API (app.py)    import pipeline
     python cli.py   POST /generate  auto_generate()
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │     pipeline.py        │
              │     auto_generate()    │
              └────────────┬───────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    PARSE DOMAIN     AI PROMPTY        GENEROWANIE
    (krok 1-2)       (krok 3-5)        (krok 6-9)
```

---

## Kroki pipeline

```
┌──────────────────────────────────────────────────┐
│  KROK 1: PARSE DOMAIN                           │
│  domain_parser.py → parse_domain()              │
│                                                  │
│  "srodawielkopolska24.pl"                        │
│    → miasto: Sroda Wielkopolska                  │
│    → display: SrodaWielkopolska24.pl             │
│    → icon_hint: stylized letters SW              │
│                                                  │
│  Baza: assets/city_adjectives.json (940 miast)   │
│  Jesli miasto nie wykryte → BLAD (uzyj generate) │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 2: PROVIDER + MODEL                       │
│  providers.py → get_provider()                   │
│                                                  │
│  config.yaml: provider = "google"                │
│    → GoogleProvider (direct Gemini API)           │
│                                                  │
│  config.yaml: provider = "openrouter"            │
│    → OpenRouterProvider (proxy, wiecej modeli)    │
│                                                  │
│  Model: config.image_model (domyslnie             │
│         gemini-3-pro-image-preview)               │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 3: HISTORIA                                │
│  history.py → get_used_labels()                  │
│                                                  │
│  Czyta output/{domain}/history.json              │
│  Ostatnie 10 uzytych motywow, np:                │
│    - Ratusz miejski                              │
│    - Klos zboza                                  │
│                                                  │
│  Przekazuje do meta-promptu jako                 │
│  "NIE POWTARZAJ tych motywow"                    │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 4: AI GENERUJE 4 PROMPTY                   │
│  providers.py → google_text_chat()               │
│  (zawsze Google Gemini direct, niezaleznie       │
│   od providera image-gen)                        │
│                                                  │
│  Laduje: prompts/meta_prompt.txt                 │
│  Wstawia zmienne:                                │
│    {miasto}, {domain}, {primary}, {accent},      │
│    {negative}, {image_template}, {history_block}  │
│                                                  │
│  AI zwraca JSON:                                 │
│  {                                               │
│    "colors": {"primary": "#C41E3A", ...},        │
│    "prompts": [                                  │
│      {"label": "Litera S z ratuszem",            │
│       "prompt": "Stworz mikroikone..."},         │
│      {"label": "Ratusz miejski", ...},           │
│      {"label": "Klos zboza", ...},               │
│      {"label": "Abstrakcyjny symbol", ...}       │
│    ]                                             │
│  }                                               │
│                                                  │
│  Model: gemini-2.5-flash (~$0.001)               │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 5: KOLORY                                  │
│  models.py → ColorPalette                        │
│                                                  │
│  Priorytet:                                      │
│    1. CLI/API override (--color1, --color2)       │
│    2. AI suggested (z kroku 4)                   │
│    3. Config default (#CC2233, #1A3A6A)          │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 6: GENEROWANIE 4 IKON                     │
│  icon_gen.py → generate_icon()                   │
│                                                  │
│  Dla kazdego prompta z kroku 4:                  │
│                                                  │
│  prompt ──→ provider.generate_image()            │
│              (Google lub OpenRouter)              │
│              │                                   │
│              ▼                                   │
│         obraz 1024px (z AI)                      │
│              │                                   │
│              ▼                                   │
│         rembg (usun tlo)                         │
│              │                                   │
│              ▼                                   │
│         autocrop (obetnij puste piksele)         │
│              │                                   │
│              ▼                                   │
│         pad 2px + kwadrat                        │
│              │                                   │
│              ▼                                   │
│         BICUBIC resize → 64x64 px                │
│              │                                   │
│              ▼                                   │
│         icon_v{N}.png                            │
│                                                  │
│  Jesli keep_originals: true → zachowaj           │
│  oryginal w original/ (domyslnie: kasuj)         │
│                                                  │
│  Koszt: 4 × ~$0.07 = ~$0.28 (gemini-3-pro)      │
│  Czas: 4 × ~25s = ~100s                         │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 7: COMPOSE LOGO                            │
│  composer.py → compose_logos()                   │
│                                                  │
│  Pillow sklada: ikona + tekst = logo .webp       │
│  Czcionka: Poppins Bold                          │
│                                                  │
│  Wersja domena:                                  │
│  ┌──────┬──────────────────────────┐             │
│  │ ICON │ SrodaWielkopolska24.pl   │             │
│  └──────┴──────────────────────────┘             │
│    → logo_v1_64.webp, logo_v1_32.webp            │
│    → logo_v2_64.webp, logo_v2_32.webp ...        │
│                                                  │
│  Wersja miasto:                                  │
│  ┌──────┬──────────────────────────┐             │
│  │ ICON │ Sroda Wielkopolska       │             │
│  └──────┴──────────────────────────┘             │
│    → miasto/logo_v1_64.webp ...                  │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 8: ZAPISZ HISTORIE                         │
│  history.py → save_prompts()                     │
│                                                  │
│  Dodaje 4 nowe prompty do                        │
│  output/{domain}/history.json                    │
│  (max 10, FIFO)                                  │
│                                                  │
│  Przy nastepnym runie AI dostanie te labelki     │
│  i zaproponuje INNE motywy                       │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 9: CLEANUP                                 │
│  cleanup.py → cleanup_output()                   │
│                                                  │
│  Usun stare runy (keep_last_runs: 3 w config)    │
│  Zostaw N najnowszych, reszte kasuj              │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
                    OUTPUT
```

---

## Struktura output

```
output/
└── srodawielkopolska24.pl/
    ├── gemini-3-pro-image-preview/    # run z modelem
    │   ├── icon_v1.png                # ikona 64x64
    │   ├── icon_v2.png
    │   ├── icon_v3.png
    │   ├── icon_v4.png
    │   ├── logo_v1_64.webp            # logo domena 64px
    │   ├── logo_v1_32.webp            # logo domena 32px
    │   ├── logo_v2_64.webp
    │   ├── ...
    │   └── miasto/
    │       ├── logo_v1_64.webp        # logo miasto 64px
    │       ├── logo_v1_32.webp
    │       └── ...
    ├── history.json                   # historia promptow
    └── metadata.json                  # wyniki ostatniego runa
```

---

## API flow

```
Klient                          Serwer (FastAPI)
  │                                │
  │  POST /generate                │
  │  {"domain": "x.pl"}           │
  │ ──────────────────────────────>│
  │                                │──→ pipeline.auto_generate()
  │  {"job_id": "abc", "running"} │     (w tle)
  │ <──────────────────────────────│
  │                                │
  │  GET /status/abc               │
  │ ──────────────────────────────>│
  │  {"status": "running"}         │
  │ <──────────────────────────────│
  │                                │     ... ~2 min ...
  │  GET /status/abc               │
  │ ──────────────────────────────>│
  │  {"status": "done",            │
  │   "icons": [...],              │
  │   "logos": [...],              │
  │   "cost_usd": 0.28}           │
  │ <──────────────────────────────│
  │                                │
  │  GET /file/x.pl/.../logo.webp  │
  │ ──────────────────────────────>│
  │  [binary .webp file]           │
  │ <──────────────────────────────│


Tryb SYNC (dla szybkich modeli):

  │  POST /generate                │
  │  {"domain": "x.pl",           │
  │   "sync": true}               │
  │ ──────────────────────────────>│
  │                                │──→ await auto_generate()
  │        ... czeka ~2 min ...    │
  │  {"status": "done",            │
  │   "icons": [...], ...}         │
  │ <──────────────────────────────│
```

---

## Providery

```
config.yaml: provider = "google"

  pipeline.py
      │
      ▼
  GoogleProvider
      │
      ▼
  https://generativelanguage.googleapis.com/v1beta/models/{model}
  Authorization: ?key=GOOGLE_API_KEY

---

config.yaml: provider = "openrouter"

  pipeline.py
      │
      ▼
  OpenRouterProvider
      │
      ▼
  https://openrouter.ai/api/v1/chat/completions
  Authorization: Bearer OPENROUTER_API_KEY

---

UWAGA: google_text_chat() (generowanie promptow)
       zawsze uzywa Google direct, niezaleznie od providera.
       Potrzebujesz GOOGLE_API_KEY nawet przy provider=openrouter.
```

---

## Historia — jak dziala deduplicacja

```
RUN 1:
  AI proponuje: [Ratusz, Kosciol, Klos, Logo mark]
  → generuje 4 ikony
  → zapisuje do history.json

RUN 2:
  Meta-prompt dostaje:
    "NIE POWTARZAJ: Ratusz, Kosciol, Klos, Logo mark"
  AI proponuje: [Fontanna, Most, Herb, Inicjaly]
  → generuje 4 nowe, inne ikony
  → dopisuje do history.json (teraz 8 wpisow)

RUN 3:
  Meta-prompt dostaje:
    "NIE POWTARZAJ: Ratusz, Kosciol, Klos, Logo mark,
     Fontanna, Most, Herb, Inicjaly"
  AI proponuje: [Park, Rzeka, Targ, Abstrakcja]
  → 4 calkowicie nowe motywy

Po 10 wpisach najstarsze sa kasowane (FIFO).
```

---

## Koszty

| Model | Koszt/ikona | 4 ikony | Szybkosc |
|-------|-------------|---------|----------|
| gemini-3-pro-image-preview | $0.070 | $0.28 | ~25s/ikona |
| gemini-2.5-flash-image | $0.003 | $0.012 | ~7s/ikona |
| google/gemini-3.1-flash (OR) | $0.010 | $0.04 | ~10s/ikona |

+ ~$0.001 za generowanie promptow (text model)

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
    PARSE DOMAIN     AI PROMPT          GENEROWANIE
    (krok 1-2)       (krok 3-5)         (krok 6-9)
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
│                                                  │
│  Baza: assets/city_adjectives.json (940 miast)   │
│  Jesli miasto nie wykryte → BLAD                 │
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
│  KROK 4: AI GENERUJE PROMPT                      │
│  providers.py → google_text_chat()               │
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
│       "prompt": "Stworz mikroikone..."}          │
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
│  KROK 6: GENEROWANIE IKONY                      │
│  icon_gen.py → generate_icon()                   │
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
│         icon.png                                 │
│                                                  │
│  Koszt: ~$0.003 (gemini-2.5-flash-image)         │
│  Czas: ~7s                                       │
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
│  ┌──────┬──────────────────────────┐             │
│  │ ICON │ SrodaWielkopolska24.pl   │             │
│  └──────┴──────────────────────────┘             │
│    → logo_v1_64.webp                             │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  KROK 8: ZAPISZ HISTORIE                         │
│  history.py → save_prompts()                     │
│                                                  │
│  Dodaje prompt do                                │
│  output/{domain}/history.json                    │
│  (max 10, FIFO)                                  │
│                                                  │
│  Przy nastepnym runie AI dostanie te labelki     │
│  i zaproponuje INNY motyw                        │
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
    ├── gemini-2.5-flash-image/
    │   ├── icon.png              # ikona 64x64
    │   └── logo_v1_64.webp       # logo = ikona + domena
    ├── history.json              # historia promptow
    └── metadata.json             # wyniki ostatniego runa
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
  │                                │     ... ~10s ...
  │  GET /status/abc               │
  │ ──────────────────────────────>│
  │  {"status": "done",            │
  │   "icon": "...",               │
  │   "logo": "...",               │
  │   "cost_usd": 0.004}          │
  │ <──────────────────────────────│
  │                                │
  │  GET /file/x.pl/.../logo.webp  │
  │ ──────────────────────────────>│
  │  [binary .webp file]           │
  │ <──────────────────────────────│


Tryb SYNC (szybszy):

  │  POST /generate                │
  │  {"domain": "x.pl",           │
  │   "sync": true}               │
  │ ──────────────────────────────>│
  │                                │──→ await auto_generate()
  │        ... czeka ~10s ...      │
  │  {"status": "done",            │
  │   "icon": "...", ...}          │
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

UWAGA: google_text_chat() (generowanie promptu)
       zawsze uzywa Google direct, niezaleznie od providera.
       Potrzebujesz GOOGLE_API_KEY nawet przy provider=openrouter.
```

---

## Historia — jak dziala deduplicacja

```
RUN 1:
  AI proponuje: "Ratusz miejski"
  → generuje ikone + logo
  → zapisuje do history.json

RUN 2:
  Meta-prompt dostaje:
    "NIE POWTARZAJ: Ratusz miejski"
  AI proponuje: "Fontanna rynkowa"
  → generuje nowa, inna ikone

RUN 3:
  Meta-prompt dostaje:
    "NIE POWTARZAJ: Ratusz miejski, Fontanna rynkowa"
  AI proponuje: "Klos zboza"
  → calkowicie nowy motyw

Po 10 wpisach najstarsze sa kasowane (FIFO).
```

---

## Koszty

| Model | Koszt/ikona | Czas |
|-------|-------------|------|
| gemini-2.5-flash-image | $0.003 | ~7s |
| gemini-3-pro-image-preview | $0.07 | ~18s |

+ ~$0.001 za generowanie promptu (text model)

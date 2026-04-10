# GeoAgent

AI-powered geolocation system that determines where a photo was taken using Claude's vision capabilities and multi-stage reasoning. Available as a CLI tool and a Telegram bot.

## How It Works

GeoAgent runs a 6-stage analysis pipeline on every image:

```
Image
  |
  v
[Stage 1] EXIF Extraction -----> GPS found? Return immediately.
  |
  v
[Stage 2] Two-Pass Visual Analysis (Extended Thinking)
  |         Pass 1: Broad sweep -- text, signs, plates, architecture,
  |                 roads, vegetation, vehicles, brands, landmarks
  |         Pass 2: Deep focus -- missed details, micro-clues,
  |                 contradictions, background analysis
  v
[Stage 3] Hypothesis Generation (Extended Thinking)
  |         Continent -> Country -> Region -> City -> Coordinates
  |         Produces 3 ranked hypotheses with confidence scores
  v
[Stage 4] Self-Verification (Extended Thinking)
  |         Re-examines the original image against each hypothesis
  |         Catches errors, adjusts locations, re-ranks
  v
[Stage 5] External Tool Verification (Full mode only)
  |         Google Places, Reverse Geocoding, Web Search
  |         Runs all checks in parallel
  v
[Stage 6] Final Scoring
            Combines all evidence -> best location + confidence
```

### What It Looks For

| Category | Examples |
|----------|----------|
| **Text & Signage** | Street signs, shop names, billboards, phone numbers, URLs, domain extensions |
| **License Plates** | Plate characters, format, color, shape, country-specific symbols |
| **Architecture** | Building style, materials, roof type, window frames, era |
| **Infrastructure** | Road markings, sign standards, utility poles, bollards, traffic lights, driving side |
| **Nature** | Plant species, terrain, soil color, climate zone, mountain shapes |
| **Vehicles** | Makes, models, market region, taxi colors, transit branding |
| **Brands** | Chain stores, telecom providers, gas stations, banks |
| **Micro-details** | Manhole covers, electrical outlets, mailbox styles, garbage bins, antenna types |

## Quick Start

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- (Optional) A Telegram bot token from [@BotFather](https://t.me/BotFather)

### Installation

```bash
git clone https://github.com/Zhaor3/GeoAgent.git
cd GeoAgent
pip install -e .
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
TELEGRAM_BOT_TOKEN=123456789:AAH...
```

See [`.env.example`](.env.example) for all available options.

## Usage

### CLI

```bash
# Analyze a local image (full mode with verification)
py -m geo_agent locate photo.jpg

# Fast mode (vision only, no external tools)
py -m geo_agent locate photo.jpg --fast

# Analyze an image from a URL
py -m geo_agent locate --url "https://example.com/photo.jpg"

# JSON output
py -m geo_agent locate photo.jpg --json

# Verbose reasoning trace
py -m geo_agent locate photo.jpg -v
```

### Telegram Bot

```bash
py -m geo_agent bot
```

Then open your bot in Telegram and send it a photo.

**Bot Commands:**

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with current settings |
| `/help` | Full command reference |
| `/settings` | View current mode, verbose state, remaining quota |
| `/mode fast` | Switch to fast mode (vision only, ~15s) |
| `/mode full` | Switch to full mode (vision + verification, ~60s) |
| `/verbose` | Toggle detailed reasoning in results |

### Docker

```bash
docker build -t geoagent .
docker run --env-file .env geoagent
```

## Architecture

```
geo_agent/
├── config.py                 # Settings (loads .env via pydantic-settings)
├── pipeline.py               # 6-stage pipeline orchestrator
├── main.py                   # Typer CLI (locate, bot)
│
├── extractors/
│   ├── exif.py               # EXIF/GPS metadata extraction (Pillow)
│   └── visual.py             # Two-pass visual analysis (Claude Vision)
│
├── reasoning/
│   ├── hypotheses.py         # Location hypothesis generation
│   ├── verify.py             # Self-verification against image
│   └── final.py              # Confidence scoring & result assembly
│
├── tools/
│   ├── base.py               # Abstract VerificationTool interface
│   ├── maps.py               # Google Places + Reverse Geocoding
│   ├── search.py             # Web search (SerpAPI)
│   └── reverse_image.py      # Reverse image search (stub)
│
├── bot/
│   ├── telegram_bot.py       # Bot setup (polling/webhook)
│   ├── handlers.py           # Command & photo handlers
│   └── formatters.py         # Result -> Telegram message formatting
│
├── models/
│   └── schemas.py            # Pydantic models (GeoResult, Hypothesis, etc.)
│
└── utils/
    ├── image.py              # Resize, base64 encode, media type detection
    ├── display.py            # Rich CLI output formatting
    └── parse.py              # Robust JSON extraction from LLM responses
```

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key |
| `TELEGRAM_BOT_TOKEN` | For bot | - | Telegram bot token from BotFather |
| `GOOGLE_MAPS_API_KEY` | No | - | Enables Places & Geocoding verification |
| `SERPAPI_KEY` | No | - | Enables web search verification |
| `MODEL_HEAVY` | No | `claude-sonnet-4-20250514` | Model for vision analysis & reasoning |
| `MODEL_LIGHT` | No | `claude-haiku-4-5-20251001` | Model for lightweight tasks |
| `THINKING_BUDGET` | No | `10000` | Extended thinking token budget per call |
| `PIPELINE_TIMEOUT` | No | `300` | Max seconds per analysis |
| `RATE_LIMIT_PER_HOUR` | No | `10` | Photo limit per Telegram user per hour |
| `MAX_IMAGE_SIZE` | No | `2048` | Max pixel dimension before resizing |

## Key Design Decisions

- **Extended Thinking** is enabled on every LLM call (10k token budget). The model reasons internally before responding, significantly improving accuracy on ambiguous images.
- **Two-pass visual extraction** catches details the first scan misses: background text, reflections, micro-details like manhole cover patterns and outlet types.
- **Self-verification loop** re-examines the original image against generated hypotheses, acting as a critical reviewer that catches errors and adjusts confidence scores.
- **Fault-tolerant pipeline** -- Pass 2 and self-verification are best-effort. If they fail, the pipeline continues with available data. Every LLM call retries once on parse failure.
- **Robust JSON parsing** handles trailing commas, comments, and markdown fences that LLMs commonly produce.

## License

Private repository. All rights reserved.

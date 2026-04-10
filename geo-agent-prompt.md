# GeoLocator Agent — Claude Code Project Prompt

## Project Overview

Build a Python-based **agentic geolocation system** that takes a single image as input and determines where in the world it was taken. The agent should mimic the workflow of tools like GeoSeer and PIGEON — using a vision LLM for visual analysis, then orchestrating multiple tool calls (maps, search, reverse image lookup) to verify and refine the guess.

The system has **two interfaces**:
1. **CLI** — for local use and testing (`python -m geo_agent locate photo.jpg`)
2. **Telegram Bot** — send a photo to the bot, it analyzes and replies with the location, map pin, and reasoning. This is the primary user-facing interface for on-the-go use.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   USER INPUT                        │
│              (image file or URL)                    │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              STAGE 1: METADATA EXTRACTION           │
│  • EXIF GPS check (instant win if present)          │
│  • Camera model, timestamp, orientation             │
│  • Strip and log metadata                           │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│           STAGE 2: VISUAL CLUE EXTRACTION           │
│  Vision LLM analyzes the image for:                 │
│  • Text / signage / language on signs               │
│  • Architecture style (colonial, brutalist, etc.)   │
│  • Vegetation type (tropical, boreal, arid)         │
│  • Road surface & markings (lane style, bollards)   │
│  • Driving side (left vs right)                     │
│  • Sun position / shadows → hemisphere hint         │
│  • Utility poles, street furniture style            │
│  • Vehicle types / license plate format             │
│  • Terrain (coastal, mountainous, flat plains)      │
│  • Weather / sky / lighting conditions              │
│                                                     │
│  OUTPUT: structured JSON of all extracted clues     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│         STAGE 3: HYPOTHESIS GENERATION              │
│  Vision LLM generates ranked location hypotheses:   │
│  • Hypothesis A: Country → Region → City (conf %)   │
│  • Hypothesis B: Country → Region → City (conf %)   │
│  • Hypothesis C: Country → Region → City (conf %)   │
│                                                     │
│  Each hypothesis includes reasoning chain           │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│          STAGE 4: TOOL-BASED VERIFICATION           │
│  For each hypothesis, the agent calls tools:        │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Google Maps  │  │ Web Search   │  │ Reverse   │  │
│  │ Places API   │  │ (extracted   │  │ Image     │  │
│  │ (landmarks,  │  │  text, sign  │  │ Search    │  │
│  │  businesses) │  │  names)      │  │ (Google   │  │
│  └──────┬──────┘  └──────┬───────┘  │  Lens)    │  │
│         │                │          └─────┬─────┘  │
│         └────────┬───────┘                │        │
│                  ▼                        │        │
│         ┌────────────────┐               │        │
│         │  Evidence       │◄──────────────┘        │
│         │  Aggregator     │                        │
│         └────────┬───────┘                         │
└──────────────────┼─────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│           STAGE 5: FINAL REASONING                  │
│  • Weigh evidence for/against each hypothesis       │
│  • Select best candidate with confidence score      │
│  • Output: GPS coords, address, reasoning trace     │
│  • Confidence: HIGH (>80%) / MED (50-80%) / LOW     │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

- **Language**: Python 3.11+
- **Agent Framework**: Use raw function-calling with the Anthropic SDK (claude-sonnet-4-20250514 with vision). Alternatively, support OpenAI GPT-4o as a fallback.
- **Image Processing**: Pillow (PIL) for EXIF extraction
- **HTTP**: httpx (async)
- **APIs to integrate**:
  - Anthropic Messages API (vision) — primary brain
  - Google Maps Places API (place search, nearby search)
  - Google Maps Geocoding API (reverse geocode candidate coords)
  - SerpAPI or Brave Search API (web search for extracted text)
  - Optional: Google Lens / reverse image search via SerpAPI
- **Config**: pydantic-settings with `.env` file for API keys
- **CLI**: typer or argparse for command-line interface
- **Telegram Bot**: python-telegram-bot v21+ (async-native). Handles photo messages, sends location pins, inline status updates.
- **Output**: Rich console output with colored confidence levels (CLI), formatted Telegram messages with emoji + map pin (bot)

---

## File Structure

```
geo-agent/
├── .env.example            # API key template
├── README.md               # Setup + usage instructions
├── requirements.txt
├── pyproject.toml
│
├── geo_agent/
│   ├── __init__.py
│   ├── main.py             # CLI entrypoint
│   ├── config.py           # pydantic-settings config loader
│   │
│   ├── pipeline.py         # Top-level orchestrator (runs stages 1-5)
│   │                       # Interface-agnostic — returns GeoResult
│   │
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── exif.py         # EXIF/metadata extraction (Pillow)
│   │   └── visual.py       # Vision LLM clue extraction (Stage 2)
│   │
│   ├── reasoning/
│   │   ├── __init__.py
│   │   ├── hypotheses.py   # Hypothesis generation (Stage 3)
│   │   └── final.py        # Final reasoning + scoring (Stage 5)
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py         # Abstract tool interface
│   │   ├── maps.py         # Google Maps Places + Geocoding
│   │   ├── search.py       # Web search (SerpAPI / Brave)
│   │   └── reverse_image.py # Reverse image search
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      # Pydantic models for clues, hypotheses, results
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py # Telegram bot main: handlers, startup, polling
│   │   ├── handlers.py     # Message handlers (photo, /start, /help, /mode)
│   │   └── formatters.py   # GeoResult → Telegram message formatting
│   │
│   └── utils/
│       ├── __init__.py
│       ├── image.py        # Image loading, resizing, base64 encoding
│       └── display.py      # Rich console output formatting
│
└── tests/
    ├── test_exif.py
    ├── test_visual.py
    ├── test_pipeline.py
    ├── test_telegram.py    # Bot handler unit tests
    └── fixtures/
        └── sample_images/  # Test images with known locations
```

---

## Key Implementation Details

### Stage 2 — Vision LLM Prompt (Critical)

The visual extraction prompt should be extremely detailed. Here's the system prompt for the vision analysis call:

```
You are an expert geolocation analyst, combining skills of a GeoGuessr 
world champion with OSINT investigator training. Analyze this image and 
extract EVERY possible geographic clue.

Return a JSON object with these fields:

{
  "text_and_signage": {
    "visible_text": ["list of all readable text"],
    "language_detected": "language code or null",
    "script_type": "latin/cyrillic/arabic/cjk/devanagari/etc or null",
    "sign_types": ["road sign", "shop sign", "street name", etc.]
  },
  "architecture": {
    "style": "description of architectural style",
    "building_materials": ["concrete", "brick", "wood", etc.],
    "roof_type": "flat/pitched/tile/metal/thatch",
    "era_estimate": "modern/colonial/soviet/medieval/etc"
  },
  "infrastructure": {
    "road_surface": "asphalt/dirt/cobblestone/concrete",
    "road_markings": "description of lane markings, colors",
    "driving_side": "left/right/unknown",
    "utility_poles": "wooden/concrete/metal/none",
    "bollard_style": "description or null",
    "street_lights": "description or null"
  },
  "nature": {
    "vegetation_type": "tropical/temperate/arid/boreal/etc",
    "specific_plants": ["palm trees", "eucalyptus", etc.],
    "terrain": "flat/hilly/mountainous/coastal/desert",
    "soil_color": "red/brown/sandy/dark/etc",
    "water_bodies": "ocean/river/lake/none"
  },
  "environmental": {
    "sun_position": "high/low/north/south based on shadows",
    "hemisphere_hint": "northern/southern/unknown",
    "season_hint": "summer/winter/rainy/dry/unknown",
    "weather": "clear/cloudy/overcast/rainy",
    "time_of_day": "morning/midday/afternoon/evening"
  },
  "vehicles_and_people": {
    "license_plate_format": "description or null",
    "vehicle_types": ["sedan", "motorcycle", "tuk-tuk", etc.],
    "vehicle_brands": ["Toyota", "Tata", etc.],
    "clothing_style": "description or null"
  },
  "distinctive_features": {
    "landmarks": ["any recognizable landmarks"],
    "brand_names": ["any visible brand/chain names"],
    "unique_clues": ["anything else distinctive"]
  },
  "overall_impression": "Free-form paragraph of your gut feeling about 
    the location based on the gestalt of all clues"
}
```

### Stage 3 — Hypothesis Generation Prompt

```
Based on the following extracted visual clues from an image, generate 
exactly 3 ranked location hypotheses. For each, provide:

1. Your best guess: Country, Region/State, City/Town
2. Confidence percentage (0-100)
3. A reasoning chain explaining which specific clues led to this guess
4. GPS coordinates estimate (lat, lng)
5. What evidence would CONFIRM this hypothesis
6. What evidence would REFUTE this hypothesis

Clues: {stage_2_output_json}

Return as a JSON array of 3 hypothesis objects.
```

### Stage 4 — Tool Verification Loop

For each hypothesis, run these tool checks in parallel (asyncio.gather):

1. **Google Places Search**: Search for any extracted business names / landmarks near the hypothesized coordinates. If matches found → boost confidence.
2. **Web Search**: Search for extracted text strings + hypothesized location. Look for matches.
3. **Reverse Geocode**: Get the address at the hypothesized coordinates. Does the area match the architectural style and vegetation described?
4. **Reverse Image Search** (optional): Find visually similar images online and check their associated locations.

Each tool returns a `ToolResult` with:
- `supports_hypothesis: bool`
- `confidence_delta: float` (how much to adjust confidence, -30 to +30)
- `evidence_summary: str`

### Stage 5 — Final Scoring

```python
# Pseudocode for final scoring
for hypothesis in hypotheses:
    base_score = hypothesis.initial_confidence
    for tool_result in hypothesis.tool_results:
        base_score += tool_result.confidence_delta
    hypothesis.final_score = clamp(base_score, 0, 100)

# Sort by final_score descending
# Winner = hypotheses[0]
```

---

## Pydantic Schemas (models/schemas.py)

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Confidence(str, Enum):
    HIGH = "HIGH"      # >80%
    MEDIUM = "MEDIUM"  # 50-80%
    LOW = "LOW"        # <50%

class VisualClues(BaseModel):
    text_and_signage: dict
    architecture: dict
    infrastructure: dict
    nature: dict
    environmental: dict
    vehicles_and_people: dict
    distinctive_features: dict
    overall_impression: str

class Hypothesis(BaseModel):
    rank: int
    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: float
    longitude: float
    confidence_pct: float = Field(ge=0, le=100)
    reasoning: str
    confirming_evidence: list[str]
    refuting_evidence: list[str]

class ToolResult(BaseModel):
    tool_name: str
    hypothesis_rank: int
    supports: bool
    confidence_delta: float = Field(ge=-30, le=30)
    evidence_summary: str
    raw_data: Optional[dict] = None

class GeoResult(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    confidence: Confidence
    confidence_pct: float
    reasoning_trace: str
    clues_used: VisualClues
    hypotheses: list[Hypothesis]
    tool_evidence: list[ToolResult]
```

---

## Telegram Bot Interface

### Overview

The Telegram bot is the primary user-facing interface. A user sends a photo → the bot downloads it, runs the full geolocation pipeline, and replies with a formatted message + a map pin location. The bot should feel snappy with live status updates so the user knows it's working.

### Bot Setup (BotFather)

1. Create bot via @BotFather → get `TELEGRAM_BOT_TOKEN`
2. Set bot commands:
   - `/start` — Welcome message with usage instructions
   - `/help` — Show what the bot can do
   - `/mode fast` — Switch to fast mode (vision-only, no tool verification)
   - `/mode full` — Switch to full mode (vision + tool verification)
   - `/verbose` — Toggle verbose reasoning in replies

### Bot Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT                          │
│                                                          │
│  User sends photo                                        │
│       │                                                  │
│       ▼                                                  │
│  ┌─────────────────────────────┐                         │
│  │  handlers.py                │                         │
│  │  • photo_handler()          │                         │
│  │  • Download highest-res     │                         │
│  │    photo via Bot API        │                         │
│  │  • Send "🔍 Analyzing..."  │                         │
│  │    status message           │                         │
│  └──────────────┬──────────────┘                         │
│                 │                                        │
│                 ▼                                        │
│  ┌─────────────────────────────┐                         │
│  │  pipeline.py (shared core)  │                         │
│  │  • Same pipeline as CLI     │                         │
│  │  • Returns GeoResult        │                         │
│  │  • Emits progress callbacks │◄── progress_callback()  │
│  └──────────────┬──────────────┘    updates the status   │
│                 │                   message in real-time  │
│                 ▼                                        │
│  ┌─────────────────────────────┐                         │
│  │  formatters.py              │                         │
│  │  • GeoResult → text msg     │                         │
│  │  • Confidence emoji/color   │                         │
│  │  • Clue summary bullets     │                         │
│  └──────────────┬──────────────┘                         │
│                 │                                        │
│                 ▼                                        │
│  Bot sends reply:                                        │
│  1. 📍 send_location(lat, lng) — clickable map pin      │
│  2. 📝 Formatted text message with results               │
│  3. (optional) 🗺️ Static map image via Maps API         │
└──────────────────────────────────────────────────────────┘
```

### Handler Implementation (handlers.py)

```python
from telegram import Update, PhotoSize
from telegram.ext import ContextTypes
from geo_agent.pipeline import run_pipeline, PipelineMode
from geo_agent.bot.formatters import format_geo_result

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 *GeoLocator Bot*\n\n"
        "Send me any photo and I'll tell you where it was taken!\n\n"
        "📸 Just send a photo — that's it.\n"
        "⚡ /mode fast — quick guess (vision only)\n"
        "🔬 /mode full — deep analysis (vision + verification)\n"
        "📋 /verbose — toggle detailed reasoning\n",
        parse_mode="Markdown"
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo: PhotoSize = update.message.photo[-1]  # highest resolution
    
    status_msg = await update.message.reply_text("🔍 Downloading image...")
    
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()
    
    user_mode = context.user_data.get("mode", PipelineMode.FAST)
    verbose = context.user_data.get("verbose", False)
    
    async def progress_callback(stage: str, detail: str):
        try:
            await status_msg.edit_text(f"{stage}\n{detail}")
        except Exception:
            pass  # Telegram rate limits, ignore
    
    await status_msg.edit_text("🧠 Analyzing visual clues...")
    
    result = await run_pipeline(
        image_bytes=bytes(image_bytes),
        mode=user_mode,
        progress_callback=progress_callback
    )
    
    await status_msg.delete()
    
    # Send location pin (clickable, opens in maps app)
    await update.message.reply_location(
        latitude=result.latitude,
        longitude=result.longitude
    )
    
    # Send formatted text result
    text = format_geo_result(result, verbose=verbose)
    await update.message.reply_text(text, parse_mode="Markdown")

async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or args[0] not in ("fast", "full"):
        await update.message.reply_text("Usage: /mode fast or /mode full")
        return
    mode = PipelineMode.FAST if args[0] == "fast" else PipelineMode.FULL
    context.user_data["mode"] = mode
    emoji = "⚡" if mode == PipelineMode.FAST else "🔬"
    await update.message.reply_text(f"{emoji} Switched to *{args[0]}* mode", parse_mode="Markdown")

async def verbose_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = context.user_data.get("verbose", False)
    context.user_data["verbose"] = not current
    state = "ON" if not current else "OFF"
    await update.message.reply_text(f"📋 Verbose mode: *{state}*", parse_mode="Markdown")
```

### Formatter Implementation (formatters.py)

```python
from geo_agent.models.schemas import GeoResult, Confidence

CONFIDENCE_EMOJI = {
    Confidence.HIGH: "🟢",
    Confidence.MEDIUM: "🟡",
    Confidence.LOW: "🔴",
}

def format_geo_result(result: GeoResult, verbose: bool = False) -> str:
    emoji = CONFIDENCE_EMOJI[result.confidence]
    
    lines = [
        f"📍 *{result.city or 'Unknown'}, {result.region or ''}, {result.country}*",
        f"🌐 `{result.latitude:.4f}, {result.longitude:.4f}`",
        f"{emoji} Confidence: *{result.confidence.value}* ({result.confidence_pct:.0f}%)",
        "",
    ]
    
    if verbose:
        lines.append("🔍 *Key Clues:*")
        clues = result.clues_used
        if clues.text_and_signage.get("language_detected"):
            lines.append(f"  • Language: {clues.text_and_signage['language_detected']}")
        if clues.infrastructure.get("driving_side") != "unknown":
            lines.append(f"  • Driving side: {clues.infrastructure['driving_side']}")
        if clues.architecture.get("style"):
            lines.append(f"  • Architecture: {clues.architecture['style']}")
        if clues.nature.get("vegetation_type"):
            lines.append(f"  • Vegetation: {clues.nature['vegetation_type']}")
        lines.append("")
        
        lines.append("🧠 *Reasoning:*")
        lines.append(f"_{result.reasoning_trace[:500]}_")
        lines.append("")
        
        if result.hypotheses:
            lines.append("📊 *All Hypotheses:*")
            for h in result.hypotheses[:3]:
                lines.append(
                    f"  {h.rank}. {h.country} → {h.region} → {h.city} "
                    f"({h.confidence_pct:.0f}%)"
                )
    
    return "\n".join(lines)
```

### Bot Main (telegram_bot.py)

```python
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters
)
from geo_agent.config import settings
from geo_agent.bot.handlers import (
    start_handler, photo_handler, mode_handler, verbose_handler
)

def run_bot():
    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", start_handler))
    app.add_handler(CommandHandler("mode", mode_handler))
    app.add_handler(CommandHandler("verbose", verbose_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    # Handle non-photo messages gracefully
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: u.message.reply_text("📸 Send me a photo to geolocate!")
    ))
    
    print("🤖 GeoLocator Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
```

### Pipeline Progress Callback

The pipeline should accept an optional async callback so the bot can show real-time status. Update `pipeline.py` to support this:

```python
from typing import Optional, Callable, Awaitable

ProgressCallback = Optional[Callable[[str, str], Awaitable[None]]]

async def run_pipeline(
    image_bytes: bytes,
    mode: PipelineMode = PipelineMode.FAST,
    progress_callback: ProgressCallback = None
) -> GeoResult:
    
    async def emit(stage: str, detail: str = ""):
        if progress_callback:
            await progress_callback(stage, detail)
    
    # Stage 1
    await emit("📋 Extracting metadata...")
    exif_data = extract_exif(image_bytes)
    if exif_data.has_gps:
        await emit("✅ GPS found in EXIF!", f"{exif_data.lat}, {exif_data.lng}")
        return build_result_from_exif(exif_data)
    
    # Stage 2
    await emit("🔍 Analyzing visual clues...")
    clues = await extract_visual_clues(image_bytes)
    
    # Stage 3
    await emit("🧠 Generating location hypotheses...")
    hypotheses = await generate_hypotheses(clues)
    
    if mode == PipelineMode.FULL:
        # Stage 4
        await emit("🔧 Verifying with external tools...")
        tool_results = await verify_hypotheses(hypotheses, clues)
        
        # Stage 5
        await emit("⚖️ Final reasoning...")
        result = await final_reasoning(hypotheses, tool_results, clues)
    else:
        result = build_result_from_hypotheses(hypotheses, clues)
    
    await emit("✅ Done!", f"{result.country}, {result.city}")
    return result
```

### Telegram Bot UX Flow

```
USER sends photo of a street in Tokyo
    │
    ▼
BOT: 🔍 Downloading image...
    │ (updates in-place)
    ▼
BOT: 🔍 Analyzing visual clues...
    │ (updates in-place)
    ▼
BOT: 🧠 Generating location hypotheses...
    │ (updates in-place)
    ▼
BOT: 🔧 Verifying with external tools...  (full mode only)
    │ (updates in-place)
    ▼
BOT: ⚖️ Final reasoning...
    │
    ▼  (status message deleted, replaced with results)
    
BOT sends: 📍 Location Pin (35.6595, 139.7004) — clickable, opens Maps

BOT sends:
┌──────────────────────────────────────┐
│ 📍 Shibuya, Kanto, Japan            │
│ 🌐 35.6595, 139.7004               │
│ 🟢 Confidence: HIGH (95%)           │
│                                      │
│ 🔍 Key Clues:                       │
│   • Language: Japanese               │
│   • Driving side: left               │
│   • Architecture: Modern commercial  │
│   • Vegetation: Temperate            │
│                                      │
│ 🧠 Reasoning:                       │
│ Japanese text on signs (kanji +      │
│ hiragana), left-hand driving, Lawson │
│ convenience store branding, and      │
│ cherry blossoms strongly indicate    │
│ urban Japan in spring...             │
└──────────────────────────────────────┘
```

### Bot Edge Cases to Handle

- **No photo sent**: Reply with "📸 Send me a photo to geolocate!"
- **Compressed photo**: Telegram compresses photos. Always use `update.message.photo[-1]` for highest resolution. Also support `update.message.document` for uncompressed images sent as files.
- **Group chats**: Bot should respond to photos only when mentioned (@botname) or replied to, to avoid spam.
- **Rate limiting**: Store per-user timestamps in `context.user_data`, limit to ~10 analyses per hour per user.
- **Large images**: Resize to max 2048px on longest side before sending to vision LLM (saves tokens/cost).
- **Timeouts**: Set a 60s timeout on the pipeline. If exceeded, reply with partial results from whatever stage completed.
- **Errors**: Catch all exceptions in the photo handler, reply with "❌ Analysis failed: {brief reason}. Try again or send a different photo."
- **Document photos**: Handle `filters.Document.IMAGE` in addition to `filters.PHOTO` for users who send uncompressed.

### Bot Deployment

- **Dev**: `python -m geo_agent.bot.telegram_bot` (polling mode)
- **Prod**: Use webhook mode behind nginx/caddy on a VPS. The bot can also run on Railway, Render, or a $5 DigitalOcean droplet.
- **Docker**: Include a `Dockerfile` that runs the bot:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  CMD ["python", "-m", "geo_agent.bot.telegram_bot"]
  ```
- **Webhook mode** (optional, for production):
  ```python
  # In telegram_bot.py, add webhook support
  if settings.TELEGRAM_WEBHOOK_URL:
      app.run_webhook(
          listen="0.0.0.0",
          port=8443,
          url_path=settings.TELEGRAM_BOT_TOKEN,
          webhook_url=f"{settings.TELEGRAM_WEBHOOK_URL}/{settings.TELEGRAM_BOT_TOKEN}"
      )
  else:
      app.run_polling()
  ```

---

## CLI Usage

```bash
# Basic usage
python -m geo_agent locate photo.jpg

# With verbose reasoning trace
python -m geo_agent locate photo.jpg --verbose

# Fast mode (skip tool verification, vision-only)
python -m geo_agent locate photo.jpg --fast

# From URL
python -m geo_agent locate --url "https://example.com/photo.jpg"

# Output as JSON
python -m geo_agent locate photo.jpg --json

# Launch Telegram bot (polling mode)
python -m geo_agent.bot.telegram_bot

# Launch Telegram bot (or via CLI command)
python -m geo_agent bot
```

---

## .env.example

```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_MAPS_API_KEY=AIza...
SERPAPI_KEY=...
# Optional: fallback to OpenAI
OPENAI_API_KEY=sk-...
# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
# Optional: set for webhook mode, leave empty for polling
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
```

---

## Implementation Priority

1. **Phase 1 (MVP)**: EXIF extraction + Vision LLM analysis + hypothesis generation + Rich CLI output. No external tool verification. This alone is surprisingly powerful.
2. **Phase 2**: Telegram bot with basic photo → analysis → text reply + location pin. Uses fast mode (vision-only). This gets the bot usable immediately.
3. **Phase 3**: Add Google Maps Places verification tool.
4. **Phase 4**: Add web search verification tool.
5. **Phase 5**: Add reverse image search tool.
6. **Phase 6**: Telegram bot polish — inline status updates, document/file support, rate limiting, group chat handling, /mode and /verbose commands.
7. **Phase 7**: Async parallel tool execution, caching, batch mode, Docker deployment, webhook mode for production.

---

## Code Style Notes

- Minimal external dependencies — prefer stdlib where possible
- Type hints everywhere
- async/await for all API calls
- No assistant-added code comments — keep it clean
- Debug-driven fixes, don't restructure working code
- Copy-paste-ready output

---

## Example Output

```
🌍 GeoLocator Agent v1.0
━━━━━━━━━━━━━━━━━━━━━━━━

📷 Analyzing: street_photo.jpg
📋 EXIF: No GPS data found | Camera: iPhone 15 Pro | Date: 2024-03-15

🔍 Extracting visual clues...
   ✓ Language detected: Japanese (kanji + hiragana on signs)
   ✓ Architecture: Modern Japanese commercial district
   ✓ Driving side: Left
   ✓ Vegetation: Temperate, cherry blossoms visible
   ✓ Distinctive: Lawson convenience store, yellow taxi

🧠 Generating hypotheses...
   1. 🇯🇵 Japan → Kanto → Tokyo, Shibuya    (87%)
   2. 🇯🇵 Japan → Kansai → Osaka, Namba      (8%)
   3. 🇯🇵 Japan → Chubu → Nagoya             (5%)

🔧 Verifying with tools...
   ✓ Google Places: Found "Lawson" at Shibuya coords → +10%
   ✓ Web Search: "渋谷" matches sign text → +5%
   ✓ Reverse Geocode: Shibuya-ku confirmed → +3%

━━━━━━━━━━━━━━━━━━━━━━━━
📍 RESULT: Tokyo, Shibuya, Japan
🌐 Coordinates: 35.6595° N, 139.7004° E
🎯 Confidence: HIGH (95%)
━━━━━━━━━━━━━━━━━━━━━━━━
```

from __future__ import annotations

import time
import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from geo_agent.config import settings
from geo_agent.models.schemas import PipelineMode
from geo_agent.pipeline import run_pipeline
from geo_agent.bot.formatters import format_geo_result


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name or "there"
    mode = context.user_data.get("mode", PipelineMode.FULL)
    mode_label = "Fast ⚡" if mode == PipelineMode.FAST else "Full 🔬"
    verbose = context.user_data.get("verbose", False)
    verbose_label = "ON" if verbose else "OFF"

    await update.message.reply_text(
        f"🌍 *Welcome to GeoLocator Bot, {name}!*\n"
        f"\n"
        f"I can figure out where a photo was taken using AI vision analysis.\n"
        f"\n"
        f"*Getting started is easy:*\n"
        f"1️⃣  Send me any photo (or drop an image file)\n"
        f"2️⃣  Wait a moment while I analyze it\n"
        f"3️⃣  Get a map pin + location with confidence score\n"
        f"\n"
        f"*Your current settings:*\n"
        f"  Mode: *{mode_label}*  |  Verbose: *{verbose_label}*\n"
        f"\n"
        f"Type /help to see all available commands.\n"
        f"\n"
        f"_Tip: Photos with visible text, signs, or landmarks work best!_",
        parse_mode="Markdown",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *All Commands*\n"
        "\n"
        "🔹 /start — Welcome message & current settings\n"
        "🔹 /help — This command list\n"
        "\n"
        "*Analysis modes:*\n"
        "🔹 /mode fast — ⚡ Quick guess using vision AI only (default)\n"
        "🔹 /mode full — 🔬 Deep analysis: vision + map/web verification\n"
        "\n"
        "*Display:*\n"
        "🔹 /verbose — Toggle detailed reasoning ON/OFF\n"
        "🔹 /settings — Show your current settings\n"
        "\n"
        "*How to send a photo:*\n"
        "📸 Send as a regular photo (compressed)\n"
        "📎 Or send as a file/document (uncompressed, better quality)\n"
        "\n"
        "*What I look for:*\n"
        "• Text & signage language\n"
        "• Architecture style\n"
        "• Road markings & driving side\n"
        "• Vegetation & terrain\n"
        "• Vehicles & license plates\n"
        "• Landmarks & brand names\n"
        "\n"
        f"_Rate limit: {settings.RATE_LIMIT_PER_HOUR} photos per hour_",
        parse_mode="Markdown",
    )


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mode = context.user_data.get("mode", PipelineMode.FULL)
    verbose = context.user_data.get("verbose", False)
    timestamps: list = context.user_data.get("request_timestamps", [])
    now = time.time()
    recent = [t for t in timestamps if now - t < 3600]
    remaining = max(0, settings.RATE_LIMIT_PER_HOUR - len(recent))

    mode_label = "⚡ Fast (vision only)" if mode == PipelineMode.FAST else "🔬 Full (vision + verification)"
    verbose_label = "📋 ON — detailed clues & reasoning" if verbose else "📋 OFF — compact results"

    await update.message.reply_text(
        "⚙️ *Your Settings*\n"
        "\n"
        f"*Mode:* {mode_label}\n"
        f"*Verbose:* {verbose_label}\n"
        f"*Photos remaining:* {remaining}/{settings.RATE_LIMIT_PER_HOUR} this hour\n"
        "\n"
        "_Change with /mode fast, /mode full, or /verbose_",
        parse_mode="Markdown",
    )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    timestamps: list = context.user_data.setdefault("request_timestamps", [])
    now = time.time()
    timestamps[:] = [t for t in timestamps if now - t < 3600]
    if len(timestamps) >= settings.RATE_LIMIT_PER_HOUR:
        await update.message.reply_text(
            "⏳ Rate limit reached. Please wait before sending more photos."
        )
        return
    timestamps.append(now)

    photo = update.message.photo[-1]
    status_msg = await update.message.reply_text("🔍 Downloading image...")

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    user_mode = context.user_data.get("mode", PipelineMode.FULL)
    verbose = context.user_data.get("verbose", False)

    async def progress_callback(stage: str, detail: str) -> None:
        try:
            await status_msg.edit_text(f"{stage}\n{detail}" if detail else stage)
        except Exception:
            pass

    await status_msg.edit_text("🧠 Analyzing visual clues...")

    try:
        result = await asyncio.wait_for(
            run_pipeline(
                image_bytes=bytes(image_bytes),
                mode=user_mode,
                progress_callback=progress_callback,
            ),
            timeout=settings.PIPELINE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        await status_msg.edit_text("⏰ Analysis timed out. Try a different photo.")
        return
    except Exception as e:
        await status_msg.edit_text(f"❌ Analysis failed: {e!s:.200}\nTry again or send a different photo.")
        return

    try:
        await status_msg.delete()
    except Exception:
        pass

    await update.message.reply_location(
        latitude=result.latitude,
        longitude=result.longitude,
    )

    text = format_geo_result(result, verbose=verbose)
    await update.message.reply_text(text, parse_mode="Markdown")


async def document_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    mime = doc.mime_type or ""
    if not mime.startswith("image/"):
        await update.message.reply_text("📸 Send me a photo to geolocate!")
        return

    user_id = update.effective_user.id
    timestamps: list = context.user_data.setdefault("request_timestamps", [])
    now = time.time()
    timestamps[:] = [t for t in timestamps if now - t < 3600]
    if len(timestamps) >= settings.RATE_LIMIT_PER_HOUR:
        await update.message.reply_text(
            "⏳ Rate limit reached. Please wait before sending more photos."
        )
        return
    timestamps.append(now)

    status_msg = await update.message.reply_text("🔍 Downloading image...")

    file = await context.bot.get_file(doc.file_id)
    image_bytes = await file.download_as_bytearray()

    user_mode = context.user_data.get("mode", PipelineMode.FULL)
    verbose = context.user_data.get("verbose", False)

    async def progress_callback(stage: str, detail: str) -> None:
        try:
            await status_msg.edit_text(f"{stage}\n{detail}" if detail else stage)
        except Exception:
            pass

    await status_msg.edit_text("🧠 Analyzing visual clues...")

    try:
        result = await asyncio.wait_for(
            run_pipeline(
                image_bytes=bytes(image_bytes),
                mode=user_mode,
                progress_callback=progress_callback,
            ),
            timeout=settings.PIPELINE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        await status_msg.edit_text("⏰ Analysis timed out. Try a different photo.")
        return
    except Exception as e:
        await status_msg.edit_text(f"❌ Analysis failed: {e!s:.200}\nTry again or send a different photo.")
        return

    try:
        await status_msg.delete()
    except Exception:
        pass

    await update.message.reply_location(
        latitude=result.latitude,
        longitude=result.longitude,
    )

    text = format_geo_result(result, verbose=verbose)
    await update.message.reply_text(text, parse_mode="Markdown")


async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or args[0] not in ("fast", "full"):
        current = context.user_data.get("mode", PipelineMode.FULL)
        current_label = "fast ⚡" if current == PipelineMode.FAST else "full 🔬"
        await update.message.reply_text(
            f"Current mode: *{current_label}*\n"
            "\n"
            "*Usage:*\n"
            "  /mode fast — ⚡ Vision AI only (quick, default)\n"
            "  /mode full — 🔬 Vision + map/web verification (thorough)",
            parse_mode="Markdown",
        )
        return
    mode = PipelineMode.FAST if args[0] == "fast" else PipelineMode.FULL
    context.user_data["mode"] = mode
    if mode == PipelineMode.FAST:
        await update.message.reply_text(
            "⚡ *Fast mode activated*\n"
            "Vision AI analysis only — quick results in seconds.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "🔬 *Full mode activated*\n"
            "Vision AI + map/web verification — slower but more accurate.\n"
            "_Requires Google Maps & SerpAPI keys for best results._",
            parse_mode="Markdown",
        )


async def verbose_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current = context.user_data.get("verbose", False)
    context.user_data["verbose"] = not current
    if not current:
        await update.message.reply_text(
            "📋 *Verbose mode: ON*\n"
            "Results will now include key clues, full reasoning, and all hypotheses.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "📋 *Verbose mode: OFF*\n"
            "Results will be compact — location, coordinates, and confidence only.",
            parse_mode="Markdown",
        )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📸 I only work with photos!\n"
        "Send me an image and I'll figure out where it was taken.\n"
        "\n"
        "_Type /help to see what I can do._",
        parse_mode="Markdown",
    )

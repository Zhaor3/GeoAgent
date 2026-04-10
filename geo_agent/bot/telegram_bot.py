from __future__ import annotations

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from geo_agent.config import settings
from geo_agent.bot.handlers import (
    start_handler,
    help_handler,
    settings_handler,
    photo_handler,
    document_photo_handler,
    mode_handler,
    verbose_handler,
    text_handler,
)


def run_bot() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        return

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("settings", settings_handler))
    app.add_handler(CommandHandler("mode", mode_handler))
    app.add_handler(CommandHandler("verbose", verbose_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.IMAGE, document_photo_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    print("🤖 GeoLocator Bot is running...")

    if settings.TELEGRAM_WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=8443,
            url_path=settings.TELEGRAM_BOT_TOKEN,
            webhook_url=f"{settings.TELEGRAM_WEBHOOK_URL}/{settings.TELEGRAM_BOT_TOKEN}",
        )
    else:
        app.run_polling()


if __name__ == "__main__":
    run_bot()

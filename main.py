import os
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Activer des logs basiques
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot en ligne !")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Echo: {update.message.text}")

if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing. Add it as an environment variable.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("echo", echo))

    logging.info("Starting bot polling...")
    app.run_polling()

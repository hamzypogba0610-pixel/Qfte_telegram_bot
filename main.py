 import os
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Bot en ligne !
Utilise /help pour voir les commandes disponibles."
    await update.message.reply_text(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Commandes disponibles :
"
        "/start - Demarrer le bot
"
        "/help - Afficher cette aide
"
        "/about - A propos du bot
"
        "/echo <texte> - Repeter un texte"
    )
    await update.message.reply_text(msg)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Bot Qfte - Developpe pour demontrer un bot Telegram simple. Heberge sur Railway."
    await update.message.reply_text(msg)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith("/echo "):
        text = text[6:]
    await update.message.reply_text("Echo: " + text)

if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing. Add it as an environment variable.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("echo", echo))

    logging.info("Starting bot polling...")
    app.run_polling()

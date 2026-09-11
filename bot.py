"""
QFTE V13 — Bot Telegram (aiogram v3)
"""

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_IDS
from logging_config import setup_logging

log = setup_logging()

# Initialisation bot & dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id not in TELEGRAM_ADMIN_IDS:
        log.warning("Unauthorized /start", user_id=message.from_user.id)
        return
    await message.answer("QFTE V13 est en ligne. Utilise /help pour la liste des commandes.")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id not in TELEGRAM_ADMIN_IDS:
        return
    help_text = (
        "Commandes disponibles :
"
        "/start — Démarrer le bot
"
        "/help — Afficher cette aide
"
        "/status — État du système
"
    )
    await message.answer(help_text)


@dp.message(Command("status"))
async def cmd_status(message: Message):
    if message.from_user.id not in TELEGRAM_ADMIN_IDS:
        return
    await message.answer("QFTE V13 : OK")


async def start_bot():
    log.info("Démarrage du bot Telegram...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_bot())

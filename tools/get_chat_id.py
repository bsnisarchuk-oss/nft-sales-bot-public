# Получение Chat ID: утилита для определения CHAT_ID Telegram-чата или канала
import asyncio
import os
from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv


async def main():
    # Загружаем .env из корня проекта (на уровень выше tools/)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    bot = Bot(
        token=os.getenv("BOT_TOKEN", ""),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    me = await bot.get_me()
    print("Bot:", me.username)

    updates = await bot.get_updates(limit=10)
    if not updates:
        print("Нет апдейтов. Напиши боту в личку сообщение и запусти снова.")
        await bot.session.close()
        return

    # берём самый свежий апдейт
    u = updates[-1]

    if u.message:
        chat = u.message.chat
        print("Chat title:", chat.title)
        print("Chat type:", chat.type)
        print("CHAT_ID:", chat.id)
    else:
        print("Последний апдейт без message. Напиши боту обычное сообщение.")

    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

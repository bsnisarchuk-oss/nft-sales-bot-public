# Тестовая отправка уведомления о продаже: отправка форматированного сообщения о продаже NFT в Telegram
import asyncio
import json
import os
from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from tools.legacy_trace_sales import parse_sales_from_trace
from utils.notifier import format_sale_message
from utils.storage import load_json
from utils.tonapi import TonApiClient


async def main():
    # Загружаем .env из корня проекта (на уровень выше tools/)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

    bot = Bot(
        token=os.getenv("BOT_TOKEN", ""),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    me = await bot.get_me()
    print("Bot:", me.username)

    chat_id = int(os.getenv("CHAT_ID", "0"))
    print("CHAT_ID:", chat_id)

    trace = json.loads(Path("data/sample_trace.json").read_text(encoding="utf-8"))
    trace_id = str(trace.get("id") or trace.get("trace_id") or "sample_trace")

    tracked = set(load_json("data/collections.json", default=[]))
    ignore = set(a.strip() for a in os.getenv("GETGEMS_ADDRESSES", "").split(",") if a.strip())

    client = TonApiClient(
        base_url=os.environ.get("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.environ.get("TONAPI_KEY", ""),
        min_interval=float(os.environ.get("TONAPI_MIN_INTERVAL", "1.1")),
    )

    try:
        sale = await parse_sales_from_trace(
            trace_id=trace_id,
            trace=trace,
            tracked_collections=tracked,
            ignore_addresses=ignore,
            tonapi_client=client,
        )

        if not sale:
            print("No sale to send.")
            return

        msg = format_sale_message(sale)
        await bot.send_message(chat_id=chat_id, text=msg, disable_web_page_preview=False)
        print("Sent test message to chat:", chat_id)

    finally:
        await client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

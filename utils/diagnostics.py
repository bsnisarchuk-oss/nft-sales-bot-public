"""
Автодиагностика для команды /health: проверка DB, TonAPI, прав бота в чате.
"""

import asyncio
from typing import Tuple

from config import GETGEMS_ADDRESSES, TONAPI_BASE_URL, TONAPI_KEY, TONAPI_MIN_INTERVAL
from utils.chat_store_bridge import all_tracked_collections
from utils.db_instance import db_ready
from utils.tonapi import TonApiClient


async def check_db() -> Tuple[bool, str]:
    """Проверяет доступность БД."""
    try:
        db = db_ready()
        if not db or not db.conn:
            return False, "DB not initialized"
        await db.conn.execute("SELECT 1")
        return True, "OK"
    except Exception as e:  # intentional: diagnostics must catch all
        return False, type(e).__name__


async def check_tonapi(timeout_sec: int = 6) -> Tuple[bool, str]:
    """Проверяет доступность TonAPI (один запрос по tracked коллекции или GETGEMS_ADDRESSES)."""
    collections = await all_tracked_collections()
    test_addr = next(iter(collections), None) if collections else None
    if not test_addr and GETGEMS_ADDRESSES:
        test_addr = GETGEMS_ADDRESSES[0]
    if not test_addr:
        return False, "No tracked collections"
    client = TonApiClient(TONAPI_BASE_URL, TONAPI_KEY, TONAPI_MIN_INTERVAL)
    try:
        await asyncio.wait_for(
            client.get_account_events(test_addr, limit=1),
            timeout=timeout_sec,
        )
        return True, "OK"
    except asyncio.TimeoutError:
        return False, "TimeoutError"
    except Exception as e:  # intentional: diagnostics must catch all
        return False, type(e).__name__
    finally:
        await client.close()


async def check_bot_can_send(bot, chat_id: int) -> Tuple[bool, str]:
    """
    Проверяем, может ли бот отправлять сообщения в чат.
    Использует get_chat_member(chat_id, bot.id) и статус/права.
    """
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
        status = (member.status if hasattr(member, "status") else "").lower()

        if status in ("creator", "administrator"):
            return True, f"OK ({status})"

        if status == "restricted":
            can_send = getattr(member, "can_send_messages", True)
            if not can_send:
                return False, "NO (restricted: can_send_messages=False)"
            return True, f"OK ({status})"

        if status in ("member", "left", "kicked"):
            if status != "member":
                return False, f"NO ({status})"
            return True, f"OK ({status})"

        return True, f"OK ({status})"
    except Exception as e:  # intentional: diagnostics must catch all
        return False, type(e).__name__

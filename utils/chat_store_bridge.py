import logging

from utils import chat_config_store, chat_store_db
from utils.db_instance import db_ready

log = logging.getLogger("chat_store_bridge")


# READ: DB если доступна, иначе JSON
async def enabled_chats() -> list[int]:
    db = db_ready()
    if db:
        return await chat_store_db.enabled_chats(db)
    return chat_config_store.enabled_chats()


async def tracked_set(chat_id: int) -> set[str]:
    db = db_ready()
    if db:
        return await chat_store_db.tracked_set(db, chat_id)
    return chat_config_store.tracked_set(chat_id)


async def all_tracked_collections() -> set[str]:
    """Все уникальные raw-адреса коллекций из всех enabled чатов."""
    db = db_ready()
    if db:
        return await chat_store_db.all_tracked_collections(db)
    return chat_config_store.all_tracked_collections()


async def get_collections(chat_id: int) -> list[dict]:
    db = db_ready()
    if db:
        return await chat_store_db.get_collections(db, chat_id)
    return chat_config_store.get_collections(chat_id)


async def list_chats() -> list[dict]:
    db = db_ready()
    if db:
        return await chat_store_db.list_chats(db)
    return chat_config_store.list_chats()


# WRITE: в оба (JSON как backup, DB как primary)
async def bind_chat(chat_id: int, title: str, added_by: int) -> None:
    db = db_ready()
    if db:
        await chat_store_db.bind_chat(db, chat_id, title, added_by)
    try:
        chat_config_store.bind_chat(chat_id, title, added_by)
    except Exception as e:  # intentional: fallback must not break primary
        log.warning("JSON backup bind_chat failed for %s: %s", chat_id, type(e).__name__)


async def set_enabled(chat_id: int, enabled: bool) -> None:
    db = db_ready()
    if db:
        await chat_store_db.set_enabled(db, chat_id, enabled)
    try:
        chat_config_store.set_enabled(chat_id, enabled)
    except Exception as e:  # intentional: fallback must not break primary
        log.warning("JSON backup set_enabled failed for %s: %s", chat_id, type(e).__name__)


async def unbind_chat(chat_id: int) -> bool:
    db = db_ready()
    if db:
        removed = await chat_store_db.unbind_chat(db, chat_id)
        try:
            chat_config_store.unbind_chat(chat_id)
        except Exception as e:  # intentional: fallback must not break primary
            log.warning("JSON backup unbind_chat failed for %s: %s", chat_id, type(e).__name__)
        return removed
    return chat_config_store.unbind_chat(chat_id)


async def add_collection(chat_id: int, raw: str, b64url: str, name: str = "") -> bool:
    db = db_ready()
    if db:
        ok = await chat_store_db.add_collection(db, chat_id, raw, b64url, name)
        try:
            chat_config_store.add_collection(chat_id, raw, b64url, name)
        except Exception as e:  # intentional: fallback must not break primary
            log.warning("JSON backup add_collection failed for %s: %s", chat_id, type(e).__name__)
        return ok
    return chat_config_store.add_collection(chat_id, raw, b64url, name)


async def remove_collection(chat_id: int, raw_or_b64: str) -> bool:
    db = db_ready()
    if db:
        ok = await chat_store_db.remove_collection(db, chat_id, raw_or_b64)
        try:
            chat_config_store.remove_collection(chat_id, raw_or_b64)
        except Exception as e:  # intentional: fallback must not break primary
            log.warning(
                "JSON backup remove_collection failed for %s: %s", chat_id, type(e).__name__
            )
        return ok
    return chat_config_store.remove_collection(chat_id, raw_or_b64)

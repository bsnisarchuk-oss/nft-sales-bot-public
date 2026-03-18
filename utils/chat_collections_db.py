from utils.db import DB


async def clear_chat_collections(db: DB, chat_id: int) -> int:
    """
    Удаляет все коллекции, привязанные к чату.
    Возвращает сколько связей удалено.
    """
    assert db.conn
    async with db.write_lock:
        cur = await db.conn.execute(
            "DELETE FROM chat_collections WHERE chat_id=?",
            (int(chat_id),),
        )
        await db.conn.commit()
        return int(cur.rowcount or 0)

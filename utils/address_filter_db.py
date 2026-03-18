"""Address filter — whitelist/blacklist seller or buyer addresses per chat.

Table: address_filters
  chat_id INTEGER
  address TEXT       — normalized raw address
  filter_type TEXT   — 'buyer_whitelist', 'buyer_blacklist', 'seller_whitelist', 'seller_blacklist'
"""

from __future__ import annotations

from utils.db import DB

VALID_TYPES = frozenset({
    "buyer_whitelist", "buyer_blacklist",
    "seller_whitelist", "seller_blacklist",
})


async def add_filter(db: DB, chat_id: int, address: str, filter_type: str) -> bool:
    """Add an address filter. Returns True if inserted, False if already exists."""
    assert filter_type in VALID_TYPES, f"Invalid filter_type: {filter_type}"
    assert db.conn
    async with db.write_lock:
        cur = await db.conn.execute(
            "SELECT 1 FROM address_filters WHERE chat_id=? AND address=? AND filter_type=?",
            (chat_id, address, filter_type),
        )
        if await cur.fetchone():
            return False
        await db.conn.execute(
            "INSERT INTO address_filters (chat_id, address, filter_type) VALUES (?,?,?)",
            (chat_id, address, filter_type),
        )
        await db.conn.commit()
    return True


async def remove_filter(db: DB, chat_id: int, address: str, filter_type: str) -> bool:
    """Remove an address filter. Returns True if removed."""
    assert db.conn
    async with db.write_lock:
        cur = await db.conn.execute(
            "DELETE FROM address_filters WHERE chat_id=? AND address=? AND filter_type=?",
            (chat_id, address, filter_type),
        )
        await db.conn.commit()
    return cur.rowcount > 0


async def list_filters(db: DB, chat_id: int, filter_type: str | None = None) -> list[dict]:
    """List address filters for a chat, optionally filtered by type."""
    assert db.conn
    if filter_type:
        cur = await db.conn.execute(
            "SELECT address, filter_type FROM address_filters WHERE chat_id=? AND filter_type=?",
            (chat_id, filter_type),
        )
    else:
        cur = await db.conn.execute(
            "SELECT address, filter_type FROM address_filters WHERE chat_id=?",
            (chat_id,),
        )
    rows = await cur.fetchall()
    return [{"address": r[0], "filter_type": r[1]} for r in rows]


async def check_sale_allowed(db: DB, chat_id: int, buyer: str, seller: str) -> bool:
    """Check if a sale passes the address filters.

    Logic:
    - If buyer_whitelist exists: buyer must be in it
    - If buyer_blacklist exists: buyer must NOT be in it
    - If seller_whitelist exists: seller must be in it
    - If seller_blacklist exists: seller must NOT be in it
    """
    assert db.conn
    cur = await db.conn.execute(
        "SELECT address, filter_type FROM address_filters WHERE chat_id=?",
        (chat_id,),
    )
    rows = await cur.fetchall()
    if not rows:
        return True

    # Group by type
    groups: dict[str, set[str]] = {}
    for addr, ft in rows:
        groups.setdefault(ft, set()).add(addr)

    # Buyer checks
    bw = groups.get("buyer_whitelist")
    if bw and buyer not in bw:
        return False
    bb = groups.get("buyer_blacklist")
    if bb and buyer in bb:
        return False

    # Seller checks
    sw = groups.get("seller_whitelist")
    if sw and seller not in sw:
        return False
    sb = groups.get("seller_blacklist")
    if sb and seller in sb:
        return False

    return True

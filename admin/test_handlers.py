from decimal import Decimal

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from admin.helpers import _admin_ids
from config import TONAPI_BASE_URL, TONAPI_KEY, TONAPI_MIN_INTERVAL
from utils.chat_store_bridge import get_collections as get_collections_for_chat
from utils.models import SaleEvent, SaleItem
from utils.notifier import format_sale_message
from utils.sale_dispatcher import dispatch_sale_to_chats
from utils.tonapi import TonApiClient

router = Router()


@router.message(Command("test"))
async def cmd_test(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer("⛔️ Нет доступа.")
        return

    fake = SaleEvent(
        trace_id="TEST_TRACE",
        buyer="0:buyer_test",
        seller="0:seller_test",
        price_ton=Decimal("1.23"),
        items=[
            SaleItem(
                nft_address="0:nft_test",
                nft_name="Test NFT #1",
                collection_address="0:collection_test",
                collection_name="Test Collection",
                nft_address_b64url="",
            )
        ],
    )
    text = format_sale_message(fake)
    await message.answer(text, disable_web_page_preview=False)


@router.message(Command("test_photo"))
async def cmd_test_photo(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer("⛔️ Нет доступа.")
        return

    # Любая картинка из интернета (заглушка)
    img = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/640px-Cat03.jpg"

    text = (
        "NFT Sale\n"
        "Price: 1.11 TON\n"
        "Buyer: 0:test_buyer\n"
        "Seller: 0:test_seller\n"
        "Trace: TEST_PHOTO\n"
        "Items: 1\n"
        "• Test Collection - Test NFT\n"
    )

    bot = message.bot
    if not bot:
        return
    await bot.send_photo(chat_id=message.chat.id, photo=img, caption=text)


@router.message(Command("test_sale"))
async def cmd_test_sale(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer("🚫 Нет доступа.")
        return

    fake = SaleEvent(
        trace_id="TEST_TRACE_MULTI",
        buyer="0:test_buyer",
        seller="0:test_seller",
        price_ton=Decimal("2.50"),
        items=[
            SaleItem(
                nft_address="0:test_nft",
                nft_name="Test NFT #777",
                collection_address="0:b77...FAKE_COLLECTION",
                collection_name="Test Collection",
                nft_address_b64url="",
            )
        ],
    )
    text = format_sale_message(fake)
    await message.answer(text, disable_web_page_preview=False)


@router.message(Command("test_route"))
async def cmd_test_route(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer("🚫 Нет доступа.")
        return

    # 1) берём адрес коллекции из команды: /test_route <addr>
    parts = (message.text or "").split(maxsplit=1)
    addr = parts[1].strip() if len(parts) == 2 else ""

    # 2) если адрес не дали — берём первую коллекцию текущего чата
    if not addr:
        cols = await get_collections_for_chat(message.chat.id)
        if not cols:
            await message.answer("Добавь коллекцию в этом чате и попробуй снова: ➕ Add collection")
            return
        addr = cols[0].get("raw") or cols[0].get("b64url") or ""

    if addr:
        client = TonApiClient(TONAPI_BASE_URL, TONAPI_KEY, TONAPI_MIN_INTERVAL)
        try:
            raw, b64url = await client.normalize_address(addr)
            addr = raw  # используем raw, потому что sale.collection_address обычно raw
        except Exception:
            pass
        finally:
            await client.close()

    fake = SaleEvent(
        trace_id="TEST_ROUTE",
        buyer="0:test_buyer",
        seller="0:test_seller",
        price_ton=Decimal("1.11"),
        items=[
            SaleItem(
                nft_address="0:test_nft",
                nft_name="Test NFT",
                collection_address=addr,  # ВАЖНО: адрес коллекции, по которому будем маршрутизировать
                collection_name="Test Collection",
                nft_address_b64url="",
            )
        ],
    )

    sent_ids = await dispatch_sale_to_chats(message.bot, fake)
    await message.answer(
        "☑ test_route\n"
        f"Текущий чат: <code>{message.chat.id}</code>\n"
        f"Адрес коллекции: <code>{addr}</code>\n"
        f"Отправлено в: <code>{', '.join(map(str, sent_ids)) if sent_ids else 'никуда'}</code>",
        parse_mode="HTML",
    )

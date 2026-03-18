from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from admin.helpers import _admin_ids, _chat_lang, _get_demo_collection_raw
from admin.keyboards import admin_main_kb, demo_kb
from utils.i18n import t
from utils.models import SaleEvent, SaleItem
from utils.sale_dispatcher import dispatch_sale_to_chat

router = Router()


@router.message(Command("demo_mode"))
async def cmd_demo_mode(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return
    lang = await _chat_lang(message.chat.id)
    await message.answer(t("demo_menu", lang), reply_markup=demo_kb(lang))


@router.message(Command("demo"))
async def cmd_demo(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return
    lang = await _chat_lang(message.chat.id)
    await message.answer(t("demo_menu", lang), reply_markup=demo_kb(lang))


@router.callback_query(F.data == "demo_menu")
async def cb_demo_menu(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return
    await state.clear()
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return
    lang = await _chat_lang(msg.chat.id)
    await msg.answer(t("demo_menu", lang), reply_markup=demo_kb(lang))
    await query.answer()


@router.callback_query(F.data == "demo_text")
async def cb_demo_text(query: CallbackQuery) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    col_raw = await _get_demo_collection_raw(msg.chat.id)
    if not col_raw:
        await msg.answer(t("add_collection_no_collections", lang))
        await query.answer()
        return

    fake = SaleEvent(
        trace_id="DEMO_TEXT",
        buyer="0:demo_buyer",
        seller="0:demo_seller",
        price_ton=Decimal("9999"),
        items=[
            SaleItem(
                nft_address="0:demo_nft_1",
                nft_name="Demo NFT #1",
                collection_address=col_raw,
                collection_name="Demo Collection",
                nft_address_b64url="",
                image_url="",
            ),
            SaleItem(
                nft_address="0:demo_nft_2",
                nft_name="Demo NFT #2",
                collection_address=col_raw,
                collection_name="Demo Collection",
                nft_address_b64url="",
                image_url="",
            ),
        ],
    )

    ok = await dispatch_sale_to_chat(
        msg.bot, msg.chat.id, fake, ignore_cooldown=True
    )
    await msg.answer(t("demo_sent", lang, result="YES" if ok else "NO"))
    await query.answer()


@router.callback_query(F.data == "demo_photo")
async def cb_demo_photo(query: CallbackQuery) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    col_raw = await _get_demo_collection_raw(msg.chat.id)
    if not col_raw:
        await msg.answer(t("add_collection_no_collections", lang))
        await query.answer()
        return

    img = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/640px-Cat03.jpg"

    fake = SaleEvent(
        trace_id="DEMO_PHOTO",
        buyer="0:demo_buyer",
        seller="0:demo_seller",
        price_ton=Decimal("9999"),
        items=[
            SaleItem(
                nft_address="0:demo_nft_photo",
                nft_name="Demo NFT (Photo)",
                collection_address=col_raw,
                collection_name="Demo Collection",
                nft_address_b64url="",
                image_url=img,
            )
        ],
    )

    ok = await dispatch_sale_to_chat(
        msg.bot, msg.chat.id, fake, ignore_cooldown=True
    )
    await msg.answer(t("demo_sent", lang, result="YES" if ok else "NO"))
    await query.answer()


@router.callback_query(F.data == "demo_album")
async def cb_demo_album(query: CallbackQuery) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    col_raw = await _get_demo_collection_raw(msg.chat.id)
    if not col_raw:
        await msg.answer(t("add_collection_no_collections", lang))
        await query.answer()
        return

    imgs = [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/640px-Cat03.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Cat_poster_1.jpg/640px-Cat_poster_1.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Felis_catus-cat_on_snow.jpg/640px-Felis_catus-cat_on_snow.jpg",
    ]

    fake = SaleEvent(
        trace_id="DEMO_ALBUM",
        buyer="0:demo_buyer",
        seller="0:demo_seller",
        price_ton=Decimal("9999"),
        items=[
            SaleItem(
                nft_address=f"0:demo_nft_{i}",
                nft_name=f"Demo NFT #{i}",
                collection_address=col_raw,
                collection_name="Demo Collection",
                nft_address_b64url="",
                image_url=imgs[i - 1],
            )
            for i in range(1, 4)
        ],
    )

    ok = await dispatch_sale_to_chat(
        msg.bot, msg.chat.id, fake, ignore_cooldown=True
    )
    await msg.answer(t("demo_sent", lang, result="YES" if ok else "NO"))
    await query.answer()


@router.callback_query(F.data == "demo_whale")
async def cb_demo_whale(query: CallbackQuery):
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    col_raw = await _get_demo_collection_raw(msg.chat.id)
    if not col_raw:
        await msg.answer(t("add_collection_no_collections", lang))
        await query.answer()
        return

    fake = SaleEvent(
        trace_id="DEMO_WHALE",
        buyer="0:demo_buyer",
        seller="0:demo_seller",
        price_ton=Decimal("9999"),
        items=[
            SaleItem(
                nft_address="0:demo_nft_whale",
                nft_name="Demo NFT (Whale)",
                collection_address=col_raw,
                collection_name="Demo Collection",
                nft_address_b64url="",
                image_url="",
            )
        ],
    )

    ok = await dispatch_sale_to_chat(
        msg.bot,
        msg.chat.id,
        fake,
        ignore_cooldown=True,
    )

    await msg.answer(t("demo_whale_sent", lang, result="YES" if ok else "NO"))
    await query.answer()


@router.callback_query(F.data == "demo_back")
async def cb_demo_back(query: CallbackQuery) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return
    lang = await _chat_lang(msg.chat.id)
    await msg.answer(t("cmd_back", lang), reply_markup=admin_main_kb(lang))
    await query.answer()

import io
import json

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from admin.helpers import _admin_ids, _chat_lang
from admin.states import ConfigStates
from utils.config_io import export_config, import_config
from utils.i18n import t

router = Router()


@router.message(Command("export_config"))
async def cmd_export_config(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    data = await export_config()
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    file = BufferedInputFile(raw, filename="nft_sales_bot_config.json")
    await message.answer_document(file, caption=t("export_ok", lang))


@router.message(Command("import_config"))
async def cmd_import_config(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    await state.update_data(import_replace=False)
    await state.set_state(ConfigStates.waiting_import_file)
    await message.answer(t("import_merge_prompt", lang))


@router.message(Command("import_config_replace"))
async def cmd_import_config_replace(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    await state.update_data(import_replace=True)
    await state.set_state(ConfigStates.waiting_import_file)
    await message.answer(t("import_replace_prompt", lang))


@router.message(ConfigStates.waiting_import_file, F.document)
async def st_import_file(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    doc = message.document
    if not doc:
        await message.answer(t("import_no_file", lang))
        await state.clear()
        return

    if doc.file_size and doc.file_size > 2_000_000:
        await message.answer(t("import_too_big", lang))
        await state.clear()
        return

    bot = message.bot
    if not bot:
        await message.answer(t("import_no_bot", lang))
        await state.clear()
        return
    file = await bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await bot.download_file(file.file_path or "", buf)
    buf.seek(0)

    try:
        data = json.loads(buf.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        await message.answer(t("import_bad_json", lang))
        await state.clear()
        return

    st = await state.get_data()
    replace = bool(st.get("import_replace", False))

    try:
        result = await import_config(data, replace=replace)
    except (ValueError, RuntimeError):
        await message.answer(t("import_error", lang))
        await state.clear()
        return

    await message.answer(
        t("import_ok", lang)
        + f"Mode: {'REPLACE' if replace else 'MERGE'}\n"
        f"chats: {result['chats_upserted']}\n"
        f"collections: {result['collections_upserted']}\n"
        f"links: {result['links_added']}\n"
        f"state_by_address: {result['state_upserted']}"
    )
    await state.clear()

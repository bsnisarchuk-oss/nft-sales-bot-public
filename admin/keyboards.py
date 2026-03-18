from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.i18n import t


# Админские клавиатуры: инлайн-кнопки для управления коллекциями.
def admin_main_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("btn_add_collection", lang), callback_data="add_collection")
    kb.button(text=t("btn_remove_collection", lang), callback_data="remove_collection")
    kb.button(text=t("btn_demo", lang), callback_data="demo_menu")
    kb.button(text=t("btn_settings", lang), callback_data="settings_menu")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def settings_kb(
    show_preview: bool,
    send_photos: bool,
    whale_threshold_ton: float = 0.0,
    whale_ping: bool = False,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    b.row(
        InlineKeyboardButton(text=t("btn_min_price", lang), callback_data="settings_min_price"),
        InlineKeyboardButton(text=t("btn_cooldown", lang), callback_data="settings_cooldown"),
        width=2,
    )

    b.row(
        InlineKeyboardButton(
            text=f"🔗 Preview: {'ON' if show_preview else 'OFF'}",
            callback_data="settings_toggle_preview",
        ),
        width=1,
    )

    b.row(
        InlineKeyboardButton(
            text=f"🖼 Photos: {'ON' if send_photos else 'OFF'}",
            callback_data="settings_toggle_photos",
        ),
        width=1,
    )

    b.row(
        InlineKeyboardButton(text=t("btn_whale_threshold", lang), callback_data="settings_whale_threshold"),
        InlineKeyboardButton(
            text=f"🏓 Ping admins: {'ON' if whale_ping else 'OFF'}",
            callback_data="settings_toggle_whale_ping",
        ),
        width=2,
    )

    b.row(
        InlineKeyboardButton(text=t("btn_reset_settings", lang), callback_data="settings_reset"),
        InlineKeyboardButton(text=t("btn_reset_collections", lang), callback_data="collections_reset_confirm"),
        width=2,
    )

    b.row(
        InlineKeyboardButton(text=t("btn_copy_settings", lang), callback_data="settings_copy"),
        width=1,
    )

    b.row(
        InlineKeyboardButton(text=t("btn_language", lang), callback_data="settings_language"),
        InlineKeyboardButton(text="🌙 Quiet hours", callback_data="settings_quiet_hours"),
        width=2,
    )

    b.row(
        InlineKeyboardButton(text=t("btn_batch_window", lang), callback_data="settings_batch_window"),
        InlineKeyboardButton(text=t("btn_template", lang), callback_data="settings_template"),
        width=2,
    )

    b.row(
        InlineKeyboardButton(text=t("btn_reset_state", lang), callback_data="state_reset_30m"),
        width=1,
    )

    b.row(
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="settings_back"),
        width=1,
    )

    return b.as_markup()


def language_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="settings_menu"),
        width=1,
    )
    return b.as_markup()


def demo_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=t("btn_demo_text", lang), callback_data="demo_text"),
        InlineKeyboardButton(text=t("btn_demo_photo", lang), callback_data="demo_photo"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text=t("btn_demo_album", lang), callback_data="demo_album"),
        width=1,
    )
    b.row(
        InlineKeyboardButton(text=t("btn_demo_whale", lang), callback_data="demo_whale"),
        width=1,
    )
    b.row(
        InlineKeyboardButton(text=t("btn_demo_back", lang), callback_data="demo_back"),
        width=1,
    )
    return b.as_markup()

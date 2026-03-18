import asyncio
import logging
import os
import time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from aiogram.types import InputMediaPhoto

from utils.chat_settings_db import get_settings
from utils.chat_store_bridge import enabled_chats, tracked_set
from utils.db_instance import db_ready
from utils.i18n import t
from utils.models import SaleEvent
from utils.notifier import format_sale_message
from utils.quiet_hours import is_quiet_now
from utils.ton_usd_rate import get_ton_usd_rate
from utils.whale_detector import record_purchase

log = logging.getLogger("sale_dispatcher")

SEND_MAX_RETRIES = 3
SEND_BACKOFF = (2, 4, 8)

_last_sent_at: dict[int, float] = {}  # cooldown по чатам


def _apply_cooldown(chat_id: int, cooldown_sec: int, ignore_cooldown: bool) -> None:
    if ignore_cooldown:
        return
    if cooldown_sec > 0:
        _last_sent_at[chat_id] = time.time()


async def _send_sale_to_chat(
    bot: Any, chat_id: int, sale: SaleEvent, ignore_cooldown: bool = False
) -> bool:
    """
    Общая логика отправки sale в один чат.
    Возвращает True если реально отправили, иначе False.
    """
    tracked = await tracked_set(chat_id)
    if not tracked:
        return False

    # Оставляем только те NFT, чья collection_address входит в tracked (raw или EQ)
    filtered_items = [it for it in sale.items if it.collection_address in tracked]
    if not filtered_items:
        return False

    # Настройки чата (min_price, cooldown, preview, photos, whale, language)
    db = db_ready()
    s = None
    lang = "ru"
    if db:
        s = await get_settings(db, chat_id)
        lang = s.language or "ru"

    # 0) quiet hours — suppress non-whale notifications
    if s and s.quiet_start and s.quiet_end:
        if is_quiet_now(s.quiet_start, s.quiet_end):
            log.info("Quiet hours active for chat %s, skipping (event=%s)", chat_id, sale.trace_id)
            return False

    # 1) фильтр min_price
    min_price = float(s.min_price_ton or 0) if s else 0.0
    if min_price > 0:
        try:
            price = float(sale.price_ton or 0)
        except (ValueError, TypeError):
            price = 0.0
        if price < min_price:
            log.info(
                "Skipped chat %s: price %.2f < min_price %.2f (event=%s)",
                chat_id, price, min_price, sale.trace_id,
            )
            return False

    # 2) cooldown — ждём окончания, а не пропускаем (чтобы не терять продажи)
    cooldown = int(s.cooldown_sec or 0) if s else 0
    if not ignore_cooldown and cooldown > 0:
        now = time.time()
        last = _last_sent_at.get(chat_id, 0.0)
        remaining = cooldown - (now - last)
        if remaining > 0:
            log.info(
                "Cooldown: waiting %.1fs before sending to chat %s (event=%s, price=%s TON)",
                remaining, chat_id, sale.trace_id, sale.price_ton,
            )
            await asyncio.sleep(remaining)

    show_preview = bool(s.show_link_preview) if s else True
    send_photos = bool(s.send_photos) if s else True

    sale_for_chat = SaleEvent(
        trace_id=sale.trace_id,
        buyer=sale.buyer,
        seller=sale.seller,
        price_ton=sale.price_ton,
        items=filtered_items,
    )

    whale_threshold = Decimal(str(s.whale_threshold_ton or 0)) if s else Decimal(0)
    is_whale = whale_threshold > 0 and sale_for_chat.price_ton >= whale_threshold

    # Sweep detection
    sweep_event = record_purchase(sale.buyer, sale.trace_id) if sale.buyer else None

    # вычисляем USD и формируем текст
    rate = await get_ton_usd_rate()
    price_usd = None
    if rate is not None:
        usd = (sale_for_chat.price_ton * Decimal(str(rate))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        price_usd = str(usd)
    log.debug("USD DEBUG ton=%s rate=%s price_usd=%s", sale_for_chat.price_ton, rate, price_usd)
    custom_tpl = s.message_template if s else ""
    text = format_sale_message(sale_for_chat, price_usd=price_usd, lang=lang, custom_template=custom_tpl)
    if is_whale and s:
        header = t("whale_header", lang, threshold=s.whale_threshold_ton)
        if s.whale_ping_admins:
            ids = [x.strip() for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
            mentions = ", ".join([f'<a href="tg://user?id={i}">{t("admin_mention", lang)}</a>' for i in ids])
            if mentions:
                header += f"{mentions}\n"
        text = header + text
    if sweep_event:
        sweep_header = t("whale_sweep", lang, buyer=f"<code>{sale.buyer[:16]}...</code>", count=sweep_event.count)
        text = sweep_header + text
    disable_preview = not show_preview

    # собираем фото
    imgs: list[str] = []
    if send_photos:
        for it in sale_for_chat.items:
            u = getattr(it, "image_url", "") or ""
            if u.startswith("http"):
                imgs.append(u)

    log.debug(
        "IMG DEBUG chat=%s photos=%s items=%s first_img=%s",
        chat_id,
        send_photos,
        len(sale_for_chat.items),
        ((getattr(sale_for_chat.items[0], "image_url", "") or "")[:120] if sale_for_chat.items else ""),
    )

    # Отправка с retry (до SEND_MAX_RETRIES попыток)
    for attempt in range(1, SEND_MAX_RETRIES + 1):
        try:
            sent_media = False

            # 1) медиа
            if imgs:
                try:
                    if len(imgs) == 1:
                        await bot.send_photo(
                            chat_id=chat_id, photo=imgs[0], caption=text, parse_mode="HTML",
                        )
                        _apply_cooldown(chat_id, cooldown, ignore_cooldown)
                        return True
                    else:
                        media = [InputMediaPhoto(media=u) for u in imgs[:4]]
                        await bot.send_media_group(chat_id=chat_id, media=media)
                    sent_media = True
                except Exception:  # intentional: fallback to text-only on any photo error
                    sent_media = False  # фото не прошло — упадём в текст

            # 2) текст
            disable_preview_effective = True if sent_media else disable_preview
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=disable_preview_effective,
            )
            _apply_cooldown(chat_id, cooldown, ignore_cooldown)
            return True

        except Exception as e:
            log.warning(
                "Send attempt %s/%s failed for chat %s: %s",
                attempt, SEND_MAX_RETRIES, chat_id, type(e).__name__,
            )
            if attempt < SEND_MAX_RETRIES:
                backoff = SEND_BACKOFF[attempt - 1] if attempt - 1 < len(SEND_BACKOFF) else 8
                await asyncio.sleep(backoff)
            else:
                log.exception("Failed to send sale to chat %s after %s attempts", chat_id, SEND_MAX_RETRIES)
                try:
                    from utils.runtime_state import mark_error
                    mark_error(f"send_message({chat_id}): failed after {SEND_MAX_RETRIES} retries")
                except Exception:
                    pass
                # Ставим в persistent queue для повторной отправки
                await _enqueue_failed(chat_id, sale)
                return False

    return False


async def _enqueue_failed(chat_id: int, sale: SaleEvent) -> None:
    """Ставим неотправленную sale в persistent queue."""
    try:
        from utils.sale_queue import enqueue
        db = db_ready()
        if db:
            await enqueue(db, chat_id, sale)
            log.info("Queued sale %s for chat %s (retry later)", sale.trace_id, chat_id)
    except Exception:
        log.warning("Failed to enqueue sale %s for chat %s", sale.trace_id, chat_id)


async def dispatch_sale_to_chats(bot: Any, sale: SaleEvent) -> list[int]:
    """
    Отправляет sale только в те чаты, где включена коллекция.
    Возвращает список chat_id, куда реально отправили.
    """
    chat_ids = await enabled_chats()
    if not chat_ids:
        log.info("No enabled chats bound; nothing to send.")
        return []

    # Логируем коллекции из продажи для диагностики
    sale_collections = list({it.collection_address for it in sale.items})
    log.debug("Dispatching sale: collections=%s to %s chats", sale_collections, len(chat_ids))

    sent_ids: list[int] = []
    for chat_id in chat_ids:
        tracked = await tracked_set(chat_id)
        log.debug("Chat %s tracked collections: %s", chat_id, list(tracked)[:3] if tracked else [])
        if await _send_sale_to_chat(bot, chat_id, sale):
            sent_ids.append(chat_id)
    return sent_ids


async def dispatch_sale_to_chat(
    bot: Any, chat_id: int, sale: SaleEvent, ignore_cooldown: bool = True
) -> bool:
    """
    Отправляет sale ТОЛЬКО в один chat_id.
    Возвращает True если реально отправили, иначе False.

    ignore_cooldown=True — чтобы демо можно было нажимать много раз подряд.
    """
    return await _send_sale_to_chat(bot, chat_id, sale, ignore_cooldown)

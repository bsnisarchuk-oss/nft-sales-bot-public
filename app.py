# ruff: noqa: E402
# Загружаем .env до импорта config — импорты после load_dotenv намеренные
import asyncio
import contextlib
import logging
import os
import time
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

# Загружаем .env до импорта config
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path, override=True)

from admin import router as admin_router
from config import (
    BOT_TOKEN,
    TONAPI_BASE_URL,
    TONAPI_KEY,
    TONAPI_MIN_INTERVAL,
    validate_config,
)
from utils.backup_db import maybe_daily_backup
from utils.chat_store_bridge import all_tracked_collections
from utils.db_instance import db_ready, get_db, init_db
from utils.event_sales import parse_sale_from_event
from utils.logger import setup_logging
from utils.metrics import start_metrics_server
from utils.runtime_state import inc_traces, mark_error, mark_sale, mark_tick
from utils.sale_dispatcher import dispatch_sale_to_chats
from utils.state_store_db import (
    clear_parse_failure,
    get_last_lt,
    is_trace_seen,
    mark_trace_seen,
    prune_recent_traces,
    quarantine_parse_failure,
    register_parse_failure,
    set_last_lt,
)
from utils.storage import ensure_file, save_json
from utils.tonapi import TonApiClient

log = logging.getLogger("app")


async def collect_new_events(
    client: TonApiClient,
    col_addr: str,
    last_lt: int,
    limit: int = 20,
    max_pages: int = 5,
) -> list[dict]:
    """
    Собираем все events новее last_lt для адреса коллекции.
    Пагинация через next_from.
    """
    before_lt: str | None = None
    collected: list[dict] = []
    seen: set[str] = set()
    pages = 0

    while pages < max_pages:
        payload = await client.get_account_events(col_addr, limit=limit, before_lt=before_lt)
        events = payload.get("events") or []
        if not events:
            break

        min_event_lt = min(int(e.get("lt", 0)) for e in events)

        for event in events:
            ev_lt = int(event.get("lt", 0))
            eid = event.get("event_id", "")
            if ev_lt > last_lt and not event.get("in_progress") and eid and eid not in seen:
                collected.append(event)
                seen.add(eid)

        if min_event_lt <= last_lt:
            break

        next_from = payload.get("next_from")
        if not next_from:
            break
        before_lt = str(next_from)
        pages += 1

    # от старых к новым
    collected.sort(key=lambda e: int(e.get("lt", 0)))
    return collected


async def polling_loop(stop_event: asyncio.Event, bot: Bot) -> None:
    data_dir = os.getenv("DATA_DIR", "data")
    processed_path = os.path.join(data_dir, "processed_events.json")
    health_path = os.path.join(data_dir, "runtime_health.json")
    ensure_file(processed_path, default_content={"last_lt_by_address": {}})
    ensure_file(
        health_path,
        default_content={
            "status": "starting",
            "started_at": int(time.time()),
            "last_loop_at": 0,
            "last_tick_done_at": 0,
            "collections": 0,
            "new_processed": 0,
        },
    )

    client = TonApiClient(
        base_url=TONAPI_BASE_URL,
        api_key=TONAPI_KEY,
        min_interval=TONAPI_MIN_INTERVAL,
    )

    log.info(
        "Polling loop started (collection-based). poll_interval=%s",
        os.getenv("POLL_INTERVAL_SEC", "15"),
    )

    # fallback last_lt (используется только если БД недоступна)
    last_lt_fallback: dict[str, int] = {}
    parse_failures_fallback: dict[tuple[str, str], int] = {}
    started_ts = int(time.time())

    def _save_health(status: str, collections: int = 0, new_processed: int = 0) -> None:
        now = int(time.time())
        save_json(
            health_path,
            {
                "status": status,
                "started_at": started_ts,
                "last_loop_at": now,
                "last_tick_done_at": now if status == "running" else 0,
                "collections": int(collections),
                "new_processed": int(new_processed),
            },
        )

    try:
        while not stop_event.is_set():
            _save_health("loop")
            # Динамически получаем список коллекций из всех enabled чатов
            collections = list(await all_tracked_collections())

            if not collections:
                _save_health("idle_no_collections", collections=0, new_processed=0)
                log.debug("No tracked collections, sleeping...")
                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=int(os.getenv("POLL_INTERVAL_SEC", "15"))
                    )
                except asyncio.TimeoutError:
                    pass
                continue

            limit = int(os.getenv("EVENTS_LIMIT", "20"))
            max_pages = int(os.getenv("MAX_PAGES_PER_TICK", "5"))
            parse_max_retries = int(os.getenv("PARSE_MAX_RETRIES", "3"))
            warm_skip = os.getenv("WARM_START_SKIP_HISTORY", "1") == "1"
            concurrency = int(os.getenv("POLL_CONCURRENCY", "5"))
            sem = asyncio.Semaphore(concurrency)

            async def _process_collection(col_addr: str) -> int:
                """Обработка одной коллекции. Возвращает кол-во обработанных events."""
                processed = 0
                async with sem:
                    mark_tick(addr=col_addr, trace_id="")

                    db = db_ready()
                    if db:
                        last_lt = await get_last_lt(db, col_addr)
                    else:
                        last_lt = int(last_lt_fallback.get(col_addr, 0) or 0)

                    # Warm start: нет курсора — ставим на последний event
                    if last_lt == 0 and warm_skip:
                        try:
                            payload = await client.get_account_events(col_addr, limit=limit)
                            events = payload.get("events") or []
                            if events:
                                max_ev_lt = max(int(e.get("lt", 0)) for e in events)
                                if db:
                                    await set_last_lt(db, col_addr, max_ev_lt)
                                else:
                                    last_lt_fallback[col_addr] = max_ev_lt
                                log.info("Warm start: set last_lt for collection %s to %s", col_addr, max_ev_lt)
                        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError):
                            log.exception("Warm start error for collection %s", col_addr)
                        return 0

                    # Собираем новые events
                    try:
                        new_events = await collect_new_events(
                            client=client,
                            col_addr=col_addr,
                            last_lt=last_lt,
                            limit=limit,
                            max_pages=max_pages,
                        )
                    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError):
                        log.exception("TonAPI error on get_events for %s", col_addr)
                        mark_error(f"get_events({col_addr}): API error")
                        return 0

                    if not new_events:
                        return 0

                    for event in new_events:
                        event_id = event.get("event_id", "")
                        ev_lt = int(event.get("lt", 0))
                        if not event_id:
                            continue

                        # Dedup
                        if db and await is_trace_seen(db, col_addr, event_id):
                            continue

                        # Парсим продажу из event
                        try:
                            sale = await parse_sale_from_event(
                                event, collection_address=col_addr, tonapi_client=client
                            )
                        except Exception as e:
                            log.exception("Parse error on event %s", event_id)
                            mark_error(f"parse_event({event_id}): parse error")

                            if db:
                                attempts = await register_parse_failure(
                                    db=db,
                                    address=col_addr,
                                    trace_id=event_id,
                                    lt=ev_lt,
                                    error_name=type(e).__name__,
                                    payload=event,
                                )
                            else:
                                fkey = (col_addr, event_id)
                                attempts = int(parse_failures_fallback.get(fkey, 0)) + 1
                                parse_failures_fallback[fkey] = attempts

                            # После лимита попыток отправляем в quarantine и двигаем курсор дальше.
                            if attempts >= parse_max_retries:
                                log.error(
                                    "Event quarantined after %s/%s parse attempts: address=%s event=%s",
                                    attempts,
                                    parse_max_retries,
                                    col_addr,
                                    event_id,
                                )
                                if db:
                                    await quarantine_parse_failure(db, col_addr, event_id)
                                    await mark_trace_seen(db, col_addr, event_id, lt=ev_lt)
                                else:
                                    parse_failures_fallback.pop((col_addr, event_id), None)

                                new_last = max(last_lt, ev_lt)
                                if db:
                                    await set_last_lt(db, col_addr, new_last)
                                else:
                                    last_lt_fallback[col_addr] = new_last
                                last_lt = new_last
                                continue

                            # Не двигаем курсор и не идём к более новым событиям этого адреса:
                            # чтобы не потерять проблемный event.
                            log.warning(
                                "Parse failed (%s/%s), will retry next tick: address=%s event=%s",
                                attempts,
                                parse_max_retries,
                                col_addr,
                                event_id,
                            )
                            break

                        # Parse успешен -> убираем из parse_failures и отмечаем dedup.
                        if db:
                            await clear_parse_failure(db, col_addr, event_id)
                            await mark_trace_seen(db, col_addr, event_id, lt=ev_lt)
                        else:
                            parse_failures_fallback.pop((col_addr, event_id), None)

                        if sale:
                            sent_ids = await dispatch_sale_to_chats(bot, sale)
                            if sent_ids:
                                log.info("Sale routed to %s chats: %s", len(sent_ids), sent_ids)
                                mark_sale(sale.trace_id)
                            else:
                                sale_collections = list({it.collection_address for it in sale.items})
                                log.info(
                                    "Sale parsed but not sent (see dispatcher logs): event=%s collections=%s price=%s TON",
                                    event_id,
                                    sale_collections[:2],
                                    sale.price_ton,
                                )
                        else:
                            # Логируем только если есть actions, но нет NftPurchase
                            actions = event.get("actions") or []
                            if actions:
                                action_types = [a.get("type") for a in actions if isinstance(a, dict)]
                                log.debug(
                                    "No NftPurchase in event=%s (action_types: %s)",
                                    event_id,
                                    action_types[:5],
                                )

                        inc_traces(1)
                        processed += 1
                        mark_tick(addr=col_addr, trace_id=event_id)

                        # Двигаем курсор
                        new_last = max(last_lt, ev_lt)
                        if db:
                            await set_last_lt(db, col_addr, new_last)
                        else:
                            last_lt_fallback[col_addr] = new_last
                        last_lt = new_last

                    # Чистим старые записи dedup
                    if db:
                        await prune_recent_traces(db, col_addr, keep=2000)

                return processed

            # Параллельная обработка коллекций (ограничено semaphore)
            poll_timeout = int(os.getenv("POLL_TICK_TIMEOUT_SEC", "120"))
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(
                        *[_process_collection(col) for col in collections],
                        return_exceptions=True,
                    ),
                    timeout=poll_timeout,
                )
            except asyncio.TimeoutError:
                log.error("Polling tick timed out after %ds", poll_timeout)
                results = []
            new_processed = 0
            for i, res in enumerate(results):
                if isinstance(res, BaseException):
                    log.error("Collection %s failed: %s", collections[i], res)
                    mark_error(f"collection({collections[i]}): {type(res).__name__}")
                else:
                    new_processed += res

            # Сохраняем fallback-состояние
            save_json(processed_path, {"last_lt_by_address": last_lt_fallback})
            _save_health("running", collections=len(collections), new_processed=new_processed)
            log.info(
                "Polling tick done. collections=%s new_processed=%s",
                len(collections),
                new_processed,
            )

            # Умный sleep с быстрым выходом
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=int(os.getenv("POLL_INTERVAL_SEC", "15"))
                )
            except asyncio.TimeoutError:
                pass

    finally:
        save_json(processed_path, {"last_lt_by_address": last_lt_fallback})
        _save_health("stopped")
        await client.close()
        log.info("Polling loop stopped")


async def main() -> None:
    setup_logging()  # уровень из LOG_LEVEL в .env

    # Validate config before anything else
    config_warnings = validate_config()
    for w in config_warnings:
        log.warning("Config: %s", w)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(admin_router)

    @dp.message(Command("id"))
    async def cmd_id(message: Message):
        from_user_id = message.from_user.id if message.from_user else "—"
        await message.answer(
            f"from_user.id: <code>{from_user_id}</code>\n"
            f"chat.id: <code>{message.chat.id}</code>\n"
            f"chat.type: <code>{message.chat.type}</code>",
            parse_mode="HTML",
        )

    # Start Prometheus metrics server (optional, port from METRICS_PORT env)
    metrics_port = int(os.getenv("METRICS_PORT", "0"))
    if metrics_port:
        start_metrics_server(metrics_port)

    # Start web dashboard (optional, port from DASHBOARD_PORT env)
    dashboard_port = int(os.getenv("DASHBOARD_PORT", "0"))
    if dashboard_port:
        try:
            import uvicorn

            from dashboard.app import create_app as create_dashboard
            dash = create_dashboard()
            config = uvicorn.Config(dash, host="0.0.0.0", port=dashboard_port, log_level="warning")
            server = uvicorn.Server(config)
            asyncio.create_task(server.serve())
            log.info("Dashboard started on port %d", dashboard_port)
        except ImportError:
            log.warning("Dashboard dependencies not installed (fastapi/uvicorn)")

    await init_db()

    async def queue_retry_loop() -> None:
        """Каждые 30 сек проверяем persistent queue и пересылаем неотправленные продажи."""
        from utils.sale_dispatcher import _send_sale_to_chat
        from utils.sale_queue import cleanup_stale, dequeue_batch, mark_failed, mark_sent

        while True:
            await asyncio.sleep(30)
            db = db_ready()
            if not db:
                continue
            try:
                batch = await dequeue_batch(db, limit=10)
                if not batch:
                    continue
                sent = 0
                for qid, chat_id, sale in batch:
                    ok = await _send_sale_to_chat(bot, chat_id, sale, ignore_cooldown=True)
                    if ok:
                        await mark_sent(db, qid)
                        sent += 1
                    else:
                        await mark_failed(db, qid, "send failed")
                cleaned = await cleanup_stale(db)
                log.info(
                    "Queue retry: batch=%s sent=%s cleaned=%s",
                    len(batch), sent, cleaned,
                )
            except Exception:
                log.exception("Queue retry loop error")

    async def backup_loop() -> None:
        """Раз в час проверяем, есть ли бэкап за сегодня."""
        while True:
            try:
                await maybe_daily_backup()
            except OSError:
                log.exception("Daily backup failed")
            await asyncio.sleep(3600)  # раз в час

    stop_event = asyncio.Event()
    poll_task = asyncio.create_task(polling_loop(stop_event, bot))
    backup_task = asyncio.create_task(backup_loop())
    queue_task = asyncio.create_task(queue_retry_loop())

    try:
        log.info("Bot starting (Telegram polling)...")
        await dp.start_polling(bot)
    except (asyncio.CancelledError, KeyboardInterrupt):
        log.info("Shutdown requested (Ctrl+C)")
    finally:
        stop_event.set()
        poll_task.cancel()
        backup_task.cancel()
        queue_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await poll_task
            await backup_task
            await queue_task
        # при остановке:
        db_conn = get_db()
        if db_conn:
            await db_conn.close()
        await bot.session.close()
        log.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())

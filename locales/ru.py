# Russian locale (default)
STRINGS: dict[str, str] = {
    # ── Access / errors ──
    "no_access": "⛔️ Нет доступа.",
    "db_not_init": "❌ DB не инициализирована.",
    "error": "Ошибка",

    # ── Sale notification (notifier.py) ──
    "sale_header": "<b>NFT Sale</b>",
    "price_label": "<b>Price:</b> {price_ton} TON 💰",
    "price_usd": "(≈ ${price_usd})",
    "buyer_label": "<b>Buyer:</b> {buyer} 🟢",
    "seller_label": "<b>Seller:</b> {seller} 🔴",
    "trace_label": "<b>Trace:</b> {trace_id} 🔗",
    "items_label": "<b>Items:</b> {count} ✨",
    "and_more": "...and {n} more",

    # ── Whale ──
    "whale_header": "🐳 <b>WHALE SALE</b> (≥ {threshold} TON)\n",
    "whale_sweep": "🧹 <b>SWEEP</b> — {buyer} bought {count} NFTs in 5 min\n",
    "admin_mention": "admin",

    # ── /start ──
    "cmd_start": "☑ NFT Sales Bot запущен. \nВыбери действие:",
    "cmd_back": "⬅️ Главное меню:",

    # ── /help ──
    "cmd_help": (
        "<b>NFT Sales Bot — Commands</b>\n\n"
        "<b>General</b>\n"
        "/start — Главное меню\n"
        "/help — Этот список команд\n"
        "/status — Uptime, продажи, ошибки\n"
        "/health — Диагностика (DB, TonAPI, права)\n\n"
        "<b>Chats</b>\n"
        "/bind — Привязать текущий чат\n"
        "/unbind — Отвязать текущий чат\n"
        "/pause — Приостановить уведомления\n"
        "/resume — Возобновить уведомления\n"
        "/chats — Список привязанных чатов\n\n"
        "<b>Collections</b>\n"
        "/collections — Список коллекций в чате\n"
        "/refresh_names — Обновить названия из TonAPI\n\n"
        "<b>Settings</b>\n"
        "/settings — Настройки чата (inline меню)\n"
        "/set_min_price &lt;TON&gt; — Мин. цена для уведомлений\n"
        "/set_cooldown &lt;sec&gt; — Кулдаун между сообщениями\n\n"
        "<b>Config</b>\n"
        "/export_config — Экспорт конфигурации (JSON)\n"
        "/import_config — Импорт (merge)\n"
        "/import_config_replace — Импорт (replace)\n"
        "/backup_now — Создать бэкап БД\n\n"
        "<b>Demo &amp; Test</b>\n"
        "/demo — Демо-режим (примеры сообщений)\n"
        "/test_route [addr] — Тест маршрутизации продажи"
    ),

    # ── /collections ──
    "no_collections": "📭 Коллекции не добавлены.",
    "collections_header": "📊 Отслеживаемые коллекции: {count} шт.\n",

    # ── /refresh_names ──
    "refresh_no_collections": "Коллекции не добавлены.",
    "refresh_all_named": "У всех коллекций уже есть названия.",
    "refresh_progress": "Обновляю названия: {count} шт...",
    "refresh_done": "Готово. Обновлено: {updated} / {total}",
    "refresh_skipped": "Не смог получить имя: {count} шт.",

    # ── /health ──
    "health_header": "<b>HEALTH</b>\n",
    "health_fix_header": "<b>Fix:</b>\n",
    "health_fix_send": ". Дай боту право писать в чат (сделай админом или включи Send Messages).",
    "health_fix_tonapi": ". Проверь TONAPI_KEY и доступность TonAPI.",
    "health_fix_db": ". Проверь DB_PATH и права на папку data/.",

    # ── /status ──
    "status_header": "<b>Status</b>",
    "status_uptime": "Uptime",
    "status_min": "мин",
    "status_last_tick": "Last tick",
    "status_last_addr": "Last addr",
    "status_last_trace": "Last trace",
    "status_traces": "Traces processed",
    "status_sales": "Sales sent",
    "status_last_sale": "Last sale",
    "status_last_sale_trace": "Last sale trace",
    "status_errors": "Errors (1h)",
    "status_last_error": "Last error",

    # ── /bind ──
    "bind_no_perms": (
        "⚠️ Я добавлен в чат, но не могу писать сообщения.\n"
        "Сделай меня админом или включи право <b>Send messages</b>."
    ),
    "bind_ok": (
        "✅ <b>Чат привязан</b>.\n"
        "Название: <b>{title}</b>\n"
        "chat_id: <code>{chat_id}</code>\n"
        "Коллекций: <b>{count}</b>\n\n"
        "Дальше: \n"
        "• Нажми ➕ <b>Add collection</b>\n"
        "• Или открой ⚙️ <b>Settings</b>\n"
        "• Проверка: /collections"
    ),

    # ── /unbind ──
    "unbind_confirm": (
        "⚠️ Ты точно хочешь отвязать этот чат?\n"
        "Коллекций привязано: <b>{count}</b>\n"
        "Это действие удалит привязку чата (коллекции сохранятся в БД).\n\n"
        "Напиши <code>YES</code> чтобы подтвердить, или <code>NO</code> чтобы отменить."
    ),
    "cancelled": "✅ Отменено.",
    "write_yes_or_no": "Напиши <code>YES</code> чтобы подтвердить, или <code>NO</code> чтобы отменить.",
    "unbind_done": "✔ Чат отвязан.",

    # ── /pause, /resume ──
    "paused": "⏸ Уведомления для этого чата приостановлены.",
    "resumed": "▶ Уведомления для этого чата включены.",

    # ── /chats ──
    "no_chats": "📭 Нет привязанных чатов. Напиши /bind в нужной группе.",
    "chats_header": "📌 Привязанные чаты:",

    # ── /backup_now ──
    "backup_ok": "✅ Backup создан: <code>{path}</code>",
    "backup_fail": "❌ Не удалось создать бэкап. Проверь права на папку data/",

    # ── Settings ──
    "settings_header": "⚙️ <b>Settings</b>",
    "min_price_prompt": "🔥 Пришли минимальную цену в TON (пример: 2.5). 0 = без фильтра.",
    "min_price_example": "Пример: /set_min_price 2.5",
    "min_price_error": "❌ Нужна цифра (TON). Пример: 2.5 или 0",
    "min_price_set": "✅ min_price_ton = {val}",
    "cooldown_prompt": "⏱ Пришли cooldown в секундах (целое число). 0 = без лимита.",
    "cooldown_example": "Пример: /set_cooldown 10",
    "cooldown_error": "❌ Нужны секунды (целое число). Пример: 10 или 0",
    "cooldown_set": "✅ cooldown_sec = {val}",
    "whale_prompt": "🐳 Пришли порог в TON (число). Продажи выше этой суммы — «кит». 0 = отключено.",
    "whale_error": "❌ Нужно число (TON). Пример: 10 или 0",
    "whale_set": "✅ whale_threshold_ton = {val}",
    "preview_toggled": "✅ Preview = {state}",
    "photos_toggled": "✅ Photos = {state}",
    "whale_ping_toggled": "✅ Ping admins = {state}",
    "settings_reset_done": "✅ Настройки сброшены.",
    "copy_prompt": "📄 Пришли chat_id, ОТКУДА копировать настройки.\nПодсказка: используй /chats чтобы увидеть chat_id.",
    "copy_error": "❌ Нужен chat_id (число). Посмотри /chats.",
    "copy_no_source": "❌ В чате-источнике нет сохранённых настроек. Сначала открой там Settings.",
    "copy_done": "✅ Настройки скопированы из <code>{chat_id}</code>.",

    # ── Collections reset ──
    "reset_collections_confirm": (
        "⚠️ Ты точно хочешь удалить ВСЕ коллекции из этого чата?\n"
        "Это действие нельзя отменить.\n\n"
        "Напиши: <code>YES</code> чтобы подтвердить, или <code>NO</code> чтобы отменить."
    ),
    "reset_collections_done": "✅ Удалено коллекций (связей): {count}",
    "reset_collections_empty": "Теперь список коллекций пуст. Проверь: /collections",

    # ── Add/remove collection ──
    "add_collection_prompt": "Пришли адрес коллекции (0:... или EQ...):",
    "remove_collection_prompt": "Пришли адрес коллекции, которую удалить (0:... или EQ...):",
    "add_collection_error": "❌ Не смог распознать адрес. Пришли ещё раз.",
    "add_collection_ok": "✅ Добавлено:\nraw: <code>{raw}</code>\nEQ: <code>{b64url}</code>",
    "add_collection_exists": "☑️ Такая коллекция уже есть.",
    "remove_collection_ok": "✅ Удалено.",
    "remove_collection_not_found": "ℹ️ Не нашёл такую коллекцию.",
    "add_collection_no_collections": "📭 В этом чате нет коллекций. Сначала добавь коллекцию: ➕ Add collection",
    "test_route_no_collection": "Добавь коллекцию в этом чате и попробуй снова: ➕ Add collection",

    # ── Config import/export ──
    "export_ok": "✅ Экспорт конфигурации (SQLite)",
    "import_merge_prompt": "📂 Пришли JSON-файл конфигурации (export_config). Режим: MERGE (добавит/обновит).",
    "import_replace_prompt": "⚠️ Пришли JSON-файл конфигурации. Режим: REPLACE (полностью заменить все настройки).",
    "import_no_file": "❌ Нет файла.",
    "import_too_big": "❌ Файл слишком большой (лимит 2MB).",
    "import_no_bot": "❌ Бот недоступен.",
    "import_bad_json": "❌ Не смог прочитать JSON. Файл должен быть UTF-8 JSON.",
    "import_error": "❌ Ошибка импорта. Проверь формат JSON-файла.",
    "import_ok": "✅ Импорт завершён.\n",

    # ── Demo ──
    "demo_menu": "🎬 Demo Mode: выбери пример",
    "demo_sent": "✅ Demo (only this chat). Отправлено: {result}",
    "demo_whale_sent": "✅ Whale demo отправлено: {result}",

    # ── Time ──
    "time_never": "никогда",
    "time_sec_ago": "{n} сек назад",
    "time_min_ago": "{n} мин назад",
    "time_hr_ago": "{n} ч назад",
    "time_day_ago": "{n} дн назад",

    # ── Buttons ──
    "btn_add_collection": "➕ Добавить коллекцию",
    "btn_remove_collection": "➖ Удалить коллекцию",
    "btn_demo": "🎬 Demo",
    "btn_settings": "⚙️ Settings",
    "btn_min_price": "🔥 Min price",
    "btn_cooldown": "⏱ Cooldown",
    "btn_whale_threshold": "🐳 Whale threshold",
    "btn_reset_settings": "📝 Reset settings",
    "btn_reset_collections": "🗑 Reset collections",
    "btn_copy_settings": "📋 Copy from chat",
    "btn_reset_state": "🔄 Reset state (30 min)",
    "btn_back": "⬅️ Back",
    "btn_demo_text": "📝 Пример сообщения",
    "btn_demo_photo": "📷 Пример с фото",
    "btn_demo_album": "🖼 Пример альбом",
    "btn_demo_whale": "🐳 Whale demo (9999 TON)",
    "btn_demo_back": "⬅️ Back",
    "btn_language": "🌐 Language",

    # ── Language ──
    "language_prompt": "Выбери язык / Choose language:",
    "language_set": "✅ Язык: Русский",

    # ── Quiet hours ──
    "quiet_hours_prompt": "🌙 Введи тихие часы (пример: 23:00-07:00). Отправь 0 для отключения.",
    "quiet_hours_set": "✅ Тихие часы: {start} — {end}",
    "quiet_hours_off": "✅ Тихие часы отключены.",
    "quiet_hours_error": "❌ Формат: ЧЧ:ММ-ЧЧ:ММ (пример: 23:00-07:00)",

    # ── Batch window ──
    "btn_batch_window": "📦 Batch window",
    "batch_prompt": "📦 Введи окно батчинга в секундах (целое число). Продажи за это окно группируются в одно сообщение.\n0 = отключено (каждая продажа отдельно).",
    "batch_error": "❌ Нужно число секунд (целое). Пример: 30 или 0",
    "batch_set": "✅ batch_window_sec = {val}",

    # ── Custom template ──
    "btn_template": "📝 Template",
    "template_prompt": (
        "📝 Введи шаблон сообщения о продаже.\n"
        "Доступные переменные:\n"
        "<code>{price_ton}</code>, <code>{price_usd}</code>, "
        "<code>{buyer}</code>, <code>{seller}</code>, "
        "<code>{nft_name}</code>, <code>{collection_name}</code>, "
        "<code>{items_count}</code>, <code>{trace_id}</code>\n\n"
        "Пример:\n<code>💎 {nft_name} sold for {price_ton} TON</code>\n\n"
        "Отправь <code>0</code> для сброса на стандартный шаблон."
    ),
    "template_set": "✅ Шаблон сохранён.",
    "template_reset": "✅ Шаблон сброшен на стандартный.",
}

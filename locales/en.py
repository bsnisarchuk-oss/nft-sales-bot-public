# English locale
STRINGS: dict[str, str] = {
    # ── Access / errors ──
    "no_access": "⛔️ Access denied.",
    "db_not_init": "❌ Database not initialized.",
    "error": "Error",

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
    "cmd_start": "☑ NFT Sales Bot is running.\nChoose an action:",
    "cmd_back": "⬅️ Main menu:",

    # ── /help ──
    "cmd_help": (
        "<b>NFT Sales Bot — Commands</b>\n\n"
        "<b>General</b>\n"
        "/start — Main menu\n"
        "/help — This command list\n"
        "/status — Uptime, sales, errors\n"
        "/health — Diagnostics (DB, TonAPI, permissions)\n\n"
        "<b>Chats</b>\n"
        "/bind — Bind current chat\n"
        "/unbind — Unbind current chat\n"
        "/pause — Pause notifications\n"
        "/resume — Resume notifications\n"
        "/chats — List bound chats\n\n"
        "<b>Collections</b>\n"
        "/collections — Collections in this chat\n"
        "/refresh_names — Refresh names from TonAPI\n\n"
        "<b>Settings</b>\n"
        "/settings — Chat settings (inline menu)\n"
        "/set_min_price &lt;TON&gt; — Min price for notifications\n"
        "/set_cooldown &lt;sec&gt; — Cooldown between messages\n\n"
        "<b>Config</b>\n"
        "/export_config — Export configuration (JSON)\n"
        "/import_config — Import (merge)\n"
        "/import_config_replace — Import (replace)\n"
        "/backup_now — Create DB backup\n\n"
        "<b>Demo &amp; Test</b>\n"
        "/demo — Demo mode (sample messages)\n"
        "/test_route [addr] — Test sale routing"
    ),

    # ── /collections ──
    "no_collections": "📭 No collections added.",
    "collections_header": "📊 Tracked collections: {count}\n",

    # ── /refresh_names ──
    "refresh_no_collections": "No collections added.",
    "refresh_all_named": "All collections already have names.",
    "refresh_progress": "Refreshing names: {count}...",
    "refresh_done": "Done. Updated: {updated} / {total}",
    "refresh_skipped": "Could not fetch name: {count}",

    # ── /health ──
    "health_header": "<b>HEALTH</b>\n",
    "health_fix_header": "<b>Fix:</b>\n",
    "health_fix_send": ". Give the bot permission to send messages (make admin or enable Send Messages).",
    "health_fix_tonapi": ". Check TONAPI_KEY and TonAPI availability.",
    "health_fix_db": ". Check DB_PATH and permissions on data/ folder.",

    # ── /status ──
    "status_header": "<b>Status</b>",
    "status_uptime": "Uptime",
    "status_min": "min",
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
        "⚠️ I've been added to the chat but can't send messages.\n"
        "Make me an admin or enable <b>Send messages</b> permission."
    ),
    "bind_ok": (
        "✅ <b>Chat bound</b>.\n"
        "Title: <b>{title}</b>\n"
        "chat_id: <code>{chat_id}</code>\n"
        "Collections: <b>{count}</b>\n\n"
        "Next steps:\n"
        "• Press ➕ <b>Add collection</b>\n"
        "• Or open ⚙️ <b>Settings</b>\n"
        "• Verify: /collections"
    ),

    # ── /unbind ──
    "unbind_confirm": (
        "⚠️ Are you sure you want to unbind this chat?\n"
        "Collections bound: <b>{count}</b>\n"
        "This will remove the chat binding (collections stay in DB).\n\n"
        "Type <code>YES</code> to confirm, or <code>NO</code> to cancel."
    ),
    "cancelled": "✅ Cancelled.",
    "write_yes_or_no": "Type <code>YES</code> to confirm, or <code>NO</code> to cancel.",
    "unbind_done": "✔ Chat unbound.",

    # ── /pause, /resume ──
    "paused": "⏸ Notifications for this chat paused.",
    "resumed": "▶ Notifications for this chat enabled.",

    # ── /chats ──
    "no_chats": "📭 No bound chats. Type /bind in the desired group.",
    "chats_header": "📌 Bound chats:",

    # ── /backup_now ──
    "backup_ok": "✅ Backup created: <code>{path}</code>",
    "backup_fail": "❌ Backup failed. Check permissions on data/ folder.",

    # ── Settings ──
    "settings_header": "⚙️ <b>Settings</b>",
    "min_price_prompt": "🔥 Send minimum price in TON (e.g. 2.5). 0 = no filter.",
    "min_price_example": "Example: /set_min_price 2.5",
    "min_price_error": "❌ Need a number (TON). Example: 2.5 or 0",
    "min_price_set": "✅ min_price_ton = {val}",
    "cooldown_prompt": "⏱ Send cooldown in seconds (integer). 0 = no limit.",
    "cooldown_example": "Example: /set_cooldown 10",
    "cooldown_error": "❌ Need an integer (seconds). Example: 10 or 0",
    "cooldown_set": "✅ cooldown_sec = {val}",
    "whale_prompt": "🐳 Send threshold in TON (number). Sales above this = whale. 0 = disabled.",
    "whale_error": "❌ Need a number (TON). Example: 10 or 0",
    "whale_set": "✅ whale_threshold_ton = {val}",
    "preview_toggled": "✅ Preview = {state}",
    "photos_toggled": "✅ Photos = {state}",
    "whale_ping_toggled": "✅ Ping admins = {state}",
    "settings_reset_done": "✅ Settings reset.",
    "copy_prompt": "📄 Send chat_id to copy settings FROM.\nHint: use /chats to see chat_id.",
    "copy_error": "❌ Need a chat_id (number). Check /chats.",
    "copy_no_source": "❌ Source chat has no saved settings. Open Settings there first.",
    "copy_done": "✅ Settings copied from <code>{chat_id}</code>.",

    # ── Collections reset ──
    "reset_collections_confirm": (
        "⚠️ Are you sure you want to delete ALL collections from this chat?\n"
        "This action cannot be undone.\n\n"
        "Type: <code>YES</code> to confirm, or <code>NO</code> to cancel."
    ),
    "reset_collections_done": "✅ Deleted collection links: {count}",
    "reset_collections_empty": "Collection list is now empty. Check: /collections",

    # ── Add/remove collection ──
    "add_collection_prompt": "Send collection address (0:... or EQ...):",
    "remove_collection_prompt": "Send collection address to remove (0:... or EQ...):",
    "add_collection_error": "❌ Could not parse address. Try again.",
    "add_collection_ok": "✅ Added:\nraw: <code>{raw}</code>\nEQ: <code>{b64url}</code>",
    "add_collection_exists": "☑️ This collection already exists.",
    "remove_collection_ok": "✅ Removed.",
    "remove_collection_not_found": "ℹ️ Collection not found.",
    "add_collection_no_collections": "📭 No collections in this chat. Add one first: ➕ Add collection",
    "test_route_no_collection": "Add a collection to this chat first: ➕ Add collection",

    # ── Config import/export ──
    "export_ok": "✅ Configuration export (SQLite)",
    "import_merge_prompt": "📂 Send the JSON config file (export_config). Mode: MERGE (add/update).",
    "import_replace_prompt": "⚠️ Send the JSON config file. Mode: REPLACE (fully replace all settings).",
    "import_no_file": "❌ No file.",
    "import_too_big": "❌ File too large (limit 2MB).",
    "import_no_bot": "❌ Bot unavailable.",
    "import_bad_json": "❌ Could not read JSON. File must be UTF-8 JSON.",
    "import_error": "❌ Import error. Check the JSON file format.",
    "import_ok": "✅ Import complete.\n",

    # ── Demo ──
    "demo_menu": "🎬 Demo Mode: choose an example",
    "demo_sent": "✅ Demo (this chat only). Sent: {result}",
    "demo_whale_sent": "✅ Whale demo sent: {result}",

    # ── Time ──
    "time_never": "never",
    "time_sec_ago": "{n}s ago",
    "time_min_ago": "{n}m ago",
    "time_hr_ago": "{n}h ago",
    "time_day_ago": "{n}d ago",

    # ── Buttons ──
    "btn_add_collection": "➕ Add collection",
    "btn_remove_collection": "➖ Remove collection",
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
    "btn_demo_text": "📝 Sample message",
    "btn_demo_photo": "📷 Sample with photo",
    "btn_demo_album": "🖼 Sample album",
    "btn_demo_whale": "🐳 Whale demo (9999 TON)",
    "btn_demo_back": "⬅️ Back",
    "btn_language": "🌐 Language",

    # ── Language ──
    "language_prompt": "Choose language / Выбери язык:",
    "language_set": "✅ Language: English",

    # ── Quiet hours ──
    "quiet_hours_prompt": "🌙 Enter quiet hours (e.g. 23:00-07:00). Send 0 to disable.",
    "quiet_hours_set": "✅ Quiet hours: {start} — {end}",
    "quiet_hours_off": "✅ Quiet hours disabled.",
    "quiet_hours_error": "❌ Format: HH:MM-HH:MM (e.g. 23:00-07:00)",

    # ── Batch window ──
    "btn_batch_window": "📦 Batch window",
    "batch_prompt": "📦 Enter batch window in seconds (integer). Sales within this window are grouped into one message.\n0 = disabled (each sale sent separately).",
    "batch_error": "❌ Need an integer (seconds). Example: 30 or 0",
    "batch_set": "✅ batch_window_sec = {val}",

    # ── Custom template ──
    "btn_template": "📝 Template",
    "template_prompt": (
        "📝 Enter a custom sale message template.\n"
        "Available variables:\n"
        "<code>{price_ton}</code>, <code>{price_usd}</code>, "
        "<code>{buyer}</code>, <code>{seller}</code>, "
        "<code>{nft_name}</code>, <code>{collection_name}</code>, "
        "<code>{items_count}</code>, <code>{trace_id}</code>\n\n"
        "Example:\n<code>💎 {nft_name} sold for {price_ton} TON</code>\n\n"
        "Send <code>0</code> to reset to default template."
    ),
    "template_set": "✅ Template saved.",
    "template_reset": "✅ Template reset to default.",
}

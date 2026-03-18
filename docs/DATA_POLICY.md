# Data Policy

## Purpose
Define what data the bot stores, why it is stored, and how to handle retention/deletion.

## Stored Data
Primary storage is SQLite (`data/bot.db`) plus small JSON operational files.

### SQLite entities
1. `chats`
   - `chat_id`, `title`, `enabled`, metadata fields.
2. `collections`
   - tracked collection addresses (`raw`, `b64url`, optional `name`).
3. `chat_collections`
   - chat-to-collection bindings.
4. `chat_settings`
   - filters and behavior settings (`min_price`, `cooldown`, etc.).
5. `state_by_address`
   - polling cursor (`last_lt`) per tracked collection.
6. `recent_traces`
   - dedup state for processed events.
7. `parse_failures`
   - parser failure diagnostics and quarantined events.

### JSON files
1. `data/runtime_health.json` (runtime heartbeat).
2. `data/processed_events.json` (fallback cursor state).
3. `data/chats_config.json` (legacy/fallback mirror).
4. `data/backups/*.db` (daily snapshots).

## Personal/Sensitive Data Classification
1. Telegram `chat_id` and chat titles are operational metadata.
2. Admin user IDs (`ADMIN_IDS`) are sensitive config values.
3. Bot token and API keys are secrets and must never be exposed.

## Retention
1. `recent_traces` is pruned continuously.
2. Backups are created daily; retention window should be defined by operator policy.
3. Quarantined parse failures are retained for debugging unless manually cleaned.

## Deletion / Right to Remove
1. Remove chat linkage via `/unbind` (chat no longer receives events).
2. For hard deletion, remove rows from SQLite:
   - `chats`
   - `chat_collections`
   - `chat_settings`
3. If required, clean legacy mirror (`chats_config.json`) as well.

## Security Requirements
1. `.env` must stay out of VCS.
2. Rotate secrets on ownership transfer.
3. Restrict host-level access to `data/` and backup files.

## Data Transfer During Sale
Recommended:
1. Transfer source code without production `.env`.
2. Provide sanitized DB export when possible.
3. Provide backup set only via secure channel.

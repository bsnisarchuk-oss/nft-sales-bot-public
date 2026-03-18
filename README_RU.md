# NFT Sales Bot (TON / TonAPI)

Telegram-бот на Python (aiogram 3), который отслеживает продажи NFT через TonAPI events API и отправляет уведомления в Telegram.

## Документация

- [Deploy](docs/DEPLOY.md) — развертывание на сервере
- [Operations](docs/OPERATIONS.md) — эксплуатация и мониторинг
- [Data policy](docs/DATA_POLICY.md) — хранение данных
- [Secret rotation](docs/SECRET_ROTATION.md) — ротация токенов
- [Buyer handover](docs/BUYER_HANDOVER.md) — передача проекта
- [Release checklist](docs/RELEASE_CHECKLIST.md) — чеклист релиза
- [Smoke test](docs/SMOKE_TEST.md) — проверка после деплоя

## Требования

- Python 3.10+
- Аккаунт на [TonAPI](https://tonapi.io) (бесплатный план достаточен)
- Telegram-бот (создать через [@BotFather](https://t.me/BotFather))

## Быстрый старт

### 1) Установка

```bash
python3.10 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2) Настройка `.env`

Открой `.env` и заполни **три обязательных** переменных:

```env
BOT_TOKEN=123456:ABC-DEF...       # от @BotFather
TONAPI_KEY=AE...                  # от tonapi.io
ADMIN_IDS=225328001               # твой Telegram user ID
```

Остальные переменные имеют разумные дефолты (см. [полный список](#переменные-окружения)).

### 3) Запуск

```bash
python app.py
```

База данных SQLite (`data/bot.db`) и директория `data/` создаются автоматически при первом запуске. Миграции не нужны — новые колонки добавляются автоматически.

> **Далее:** добавь бота в чат, выполни `/bind`, затем добавь коллекцию — и бот начнёт отправлять уведомления о продажах.

## Описание

Бот мониторит NFT-коллекции напрямую через TonAPI events API (`/v2/accounts/{collection}/events`), парсит события продаж и отправляет уведомления в Telegram.

### Поддерживаемые типы событий
- **NftPurchase** — продажи на GetGems и стандартных маркетплейсах
- **TelemintDeployV2** — покупки на Fragment (Telegram Numbers, Usernames и др.)
- **AuctionBid** — ставки на аукционах Fragment

### Основные возможности
- Отслеживание продаж NFT в реальном времени
- Multi-chat поддержка: работа с несколькими чатами одновременно
- Фильтрация по коллекциям для каждого чата отдельно
- Настройки per-chat: min_price, cooldown, whale alerts, фото
- Конвертация цены TON в USD (Binance)
- Persistent queue — продажи не теряются при сбое отправки
- Параллельный polling коллекций (semaphore-based)
- Автобэкап SQLite (ежедневно)
- Export/import конфигурации
- Админ-панель с inline-клавиатурами

### Расширенные возможности

- **i18n (English / Русский)** — полная локализация интерфейса и уведомлений, язык per-chat
- **Sweep detection** — обнаружение массовых скупок (3+ NFT за 5 мин от одного buyer)
- **Тихие часы** — отключение уведомлений в заданное время (напр. 23:00–07:00), whale alerts пробивают тишину
- **Батчинг сообщений** — группировка нескольких продаж в одно сообщение
- **Фильтры по адресам** — whitelist/blacklist для buyer/seller per-chat
- **Кастомные шаблоны** — пользовательские шаблоны сообщений с переменными `{price_ton}`, `{buyer}`, `{nft_name}` и др.
- **Circuit breaker** — автоматическое отключение polling при серии ошибок TonAPI
- **Валидация конфига** — проверка обязательных и опциональных переменных при старте
- **Digest-режим** — периодические сводки продаж вместо отдельных уведомлений
- **Prometheus-метрики** — экспорт метрик (sales, errors, poll duration) на отдельном порту
- **Web-дашборд** — FastAPI UI + JSON API для мониторинга (`/api/status`, `/api/chats`, `/api/health`)
- **PostgreSQL** — опциональный backend вместо SQLite (автоопределение по `DATABASE_URL`)

## Multi-chat

Бот поддерживает работу с несколькими чатами одновременно. Каждый чат может иметь свой собственный список отслеживаемых коллекций.

### Настройка чата:

1. **Добавь бота в чат** и дай ему права на отправку сообщений

2. **Привяжи чат к боту:**
   ```
   /bind
   ```

3. **Добавь коллекции для отслеживания** через кнопку "Add collection" или:
   ```
   /start → + Add collection
   ```
   Отправь адрес коллекции (формат: `0:...` или `EQ...`)

4. **Управление уведомлениями:**
   ```
   /pause   # Приостановить уведомления
   /resume  # Возобновить уведомления
   ```

5. **Просмотр списка чатов:**
   ```
   /chats
   ```

### Удаление чата:
```
/unbind
```

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/help` | Список команд |
| `/bind` | Привязать текущий чат |
| `/unbind` | Отвязать текущий чат |
| `/collections` | Показать коллекции чата |
| `/chats` | Все привязанные чаты |
| `/settings` | Настройки чата (inline-клавиатура) |
| `/status` | Статус бота (uptime, sales, errors, queue) |
| `/health` | Автодиагностика (DB, TonAPI, права в чате) |
| `/pause` / `/resume` | Пауза / возобновление |
| `/backup_now` | Ручной бэкап БД |
| `/export_config` | Экспорт конфигурации в JSON |
| `/import_config` | Импорт конфигурации (merge) |
| `/import_config_replace` | Импорт конфигурации (полная замена) |
| `/refresh_names` | Обновить названия коллекций из API |
| `/demo` | Демо-режим (отправка тестовых продаж) |

## Структура проекта

```
.
├── app.py                      # Точка входа: polling loop + dispatcher
├── config.py                   # Конфигурация из .env + валидация
├── admin/
│   ├── handlers.py             # Регистрация роутеров
│   ├── commands.py             # /start, /help, /bind, /status, /health ...
│   ├── settings_handlers.py    # /settings — inline-клавиатура настроек
│   ├── config_handlers.py      # /export_config, /import_config
│   ├── demo_handlers.py        # /demo — тестовые уведомления
│   ├── test_handlers.py        # /test, /test_route — отладка маршрутизации
│   ├── helpers.py              # Общие утилиты админ-хендлеров
│   ├── keyboards.py            # Inline-клавиатуры (i18n)
│   └── states.py               # FSM-состояния
├── locales/
│   ├── ru.py                   # Русская локализация (~170 ключей)
│   └── en.py                   # English localization (~170 keys)
├── utils/
│   ├── event_sales.py          # Парсинг NftPurchase/Telemint/Auction events
│   ├── sale_dispatcher.py      # Маршрутизация продаж по чатам + фильтры
│   ├── sale_queue.py           # Persistent queue (retry при сбое отправки)
│   ├── notifier.py             # Форматирование и отправка сообщений
│   ├── tonapi.py               # Клиент TonAPI + circuit breaker
│   ├── ton_usd_rate.py         # Курс TON/USD через Binance
│   ├── i18n.py                 # Система локализации: t(key, lang, **kwargs)
│   ├── circuit_breaker.py      # Circuit breaker (CLOSED/OPEN/HALF_OPEN)
│   ├── whale_detector.py       # Sweep detection (массовые скупки)
│   ├── quiet_hours.py          # Тихие часы
│   ├── batch_accumulator.py    # Батчинг сообщений
│   ├── address_filter_db.py    # Фильтры по buyer/seller адресам
│   ├── digest.py               # Digest-режим (сводки продаж)
│   ├── metrics.py              # Prometheus-метрики (опционально)
│   ├── db.py                   # SQLite: схема, подключение, миграции
│   ├── db_postgres.py          # PostgreSQL backend (asyncpg)
│   ├── db_protocol.py          # Абстрактный интерфейс БД
│   ├── db_instance.py          # Выбор backend (SQLite/PostgreSQL)
│   ├── chat_settings_db.py     # ChatSettings per-chat (dataclass)
│   ├── chat_store_bridge.py    # Bridge: DB (primary) + JSON (fallback)
│   ├── models.py               # Dataclasses: SaleEvent, SaleItem
│   └── config_io.py            # Export/import конфигурации
├── dashboard/
│   └── app.py                  # FastAPI web-дашборд + JSON API
├── tools/                      # Вспомогательные скрипты (диагностика, миграции)
├── tests/                      # Unit-тесты (341 тест)
├── docs/                       # Документация (deploy, operations, handover)
└── data/                       # SQLite, бэкапы (создаётся автоматически)
```

## Переменные окружения

### Обязательные

| Переменная | Описание |
|-----------|----------|
| `BOT_TOKEN` | Токен Telegram-бота |
| `TONAPI_KEY` | API ключ TonAPI |
| `ADMIN_IDS` | ID администраторов (через запятую) |

### Polling и TonAPI

| Переменная | Описание | По умолчанию |
|-----------|----------|:------------:|
| `POLL_INTERVAL_SEC` | Интервал опроса (сек) | 15 |
| `POLL_CONCURRENCY` | Параллельных запросов к TonAPI | 5 |
| `POLL_TICK_TIMEOUT_SEC` | Таймаут одного цикла polling (сек) | 120 |
| `EVENTS_LIMIT` | Лимит events за запрос | 20 |
| `TONAPI_BASE_URL` | Base URL TonAPI | https://tonapi.io |
| `TONAPI_MIN_INTERVAL` | Мин. интервал между запросами (сек) | 1.1 |
| `TON_USD_CACHE_TTL` | TTL кэша курса (сек) | 60 |

### Circuit breaker

| Переменная | Описание | По умолчанию |
|-----------|----------|:------------:|
| `CB_FAILURE_THRESHOLD` | Ошибок до размыкания | 5 |
| `CB_RECOVERY_TIMEOUT` | Время восстановления (сек) | 60 |

### Данные и логирование

| Переменная | Описание | По умолчанию |
|-----------|----------|:------------:|
| `DATA_DIR` | Директория для данных | data |
| `DB_PATH` | Путь к SQLite | data/bot.db |
| `DATABASE_URL` | PostgreSQL DSN (опционально) | — |
| `LOG_LEVEL` | Уровень логирования | INFO |

### Мониторинг (опционально)

| Переменная | Описание | По умолчанию |
|-----------|----------|:------------:|
| `METRICS_PORT` | Порт Prometheus-метрик (0 = выключено) | 0 |
| `DASHBOARD_PORT` | Порт веб-дашборда (0 = выключено) | 0 |

## PostgreSQL (опционально)

По умолчанию бот использует SQLite. Для переключения на PostgreSQL:

```bash
pip install asyncpg
```

Задай `DATABASE_URL` в `.env`:

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/nft_sales_bot
```

Бот автоматически определит backend и создаст таблицы при первом запуске.

## Web-дашборд (опционально)

```bash
pip install fastapi uvicorn
```

Задай порт в `.env`:

```env
DASHBOARD_PORT=8080
```

Endpoints:
- `GET /` — HTML-дашборд (uptime, sales, errors)
- `GET /api/status` — JSON-статус бота
- `GET /api/chats` — список привязанных чатов
- `GET /api/health` — проверка DB и TonAPI

## Prometheus-метрики (опционально)

```bash
pip install prometheus-client
```

```env
METRICS_PORT=9090
```

Метрики: `nft_sales_total`, `nft_sales_sent`, `nft_poll_duration_seconds`, `nft_circuit_breaker_state`, `nft_errors_total`.

## Тесты

```bash
pip install -r requirements-dev.txt

# Запуск тестов
pytest -q tests/

# С coverage
pytest --cov=admin --cov=utils --cov-report=term-missing tests/

# Линтер и типы
ruff check .
mypy app.py admin/ utils/ --ignore-missing-imports
```

## Docker

### Запуск через Docker Compose
```bash
docker-compose up -d
```

### Остановка
```bash
docker-compose down
```

### Просмотр логов
```bash
docker-compose logs -f bot
```

### Статус healthcheck
```bash
docker-compose ps
```

## Troubleshooting

| Проблема | Причина | Решение |
|----------|---------|---------|
| Бот не отвечает на команды | Нет прав в чате / бот не админ | Дай боту права на отправку сообщений |
| `ADMIN_IDS` — команды не работают | Неправильный user ID | Узнай свой ID через [@userinfobot](https://t.me/userinfobot) |
| `TonAPI 429 Too Many Requests` | Превышен rate limit | Увеличь `TONAPI_MIN_INTERVAL` (напр. 2.0) |
| Уведомления не приходят | Чат не привязан или нет коллекций | Выполни `/bind`, затем добавь коллекцию |
| `DB locked` при запуске | Другой процесс бота уже запущен | Останови предыдущий процесс |
| Продажи дублируются | — | Проверь, что запущен только один экземпляр бота |
| `CircuitOpenError` в логах | TonAPI недоступен | Бот автовосстановится через `CB_RECOVERY_TIMEOUT` сек |

## Лицензия

MIT

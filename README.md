# HSE Sport Centre — Telegram Mini App

Запись студентов НИУ ВШЭ на спортивные секции: каталог секций, расписание,
запись/отмена, посещаемость по датам, новости. Роли: студент, тренер, администратор.

## Стек

- Backend: FastAPI (Python), raw SQL через `psycopg2` (без ORM)
- Frontend: чистые HTML/CSS/JS, без фреймворков и сборщиков
- БД: Postgres (рекомендуется [Neon](https://neon.tech) — serverless, есть pooled-connection)
- Деплой: Vercel (frontend — статика из `public/`, backend — serverless-функция `api/index.py`)

## Структура

```
api/
  index.py           # точка входа FastAPI, сборка роутеров, /api/health, /api/me
  auth.py            # валидация Telegram initData, роли, upsert пользователя
  db.py              # подключение к Postgres, query_all/query_one/execute
  bot_notify.py       # отправка сообщений через Bot API
  routes_student.py   # секции, запись/отмена, мои записи и посещаемость
  routes_trainer.py   # расписание, генерация занятий, посещаемость
  routes_admin.py     # назначение ролей, CRUD секций
  routes_news.py       # новости + broadcast студентам
public/
  index.html
  css/style.css
  js/api.js            # обёртка над fetch с заголовком initData
  js/app.js             # весь UI: рендер по ролям, переключение вкладок
schema.sql             # DDL для Postgres
vercel.json
requirements.txt
.env.example
```

## Роли и назначение

- **student** — по умолчанию для любого нового пользователя.
- **trainer** / **admin** — назначаются администратором через вкладку «Пользователи»,
  либо бутстрап-переменными окружения `ADMIN_TG_IDS` / `TRAINER_TG_IDS`
  (список telegram id через запятую) — роль присваивается автоматически при первом входе
  и не понижается обратно переменной окружения.

## Локальный запуск

1. Создайте БД в Neon (или локальный Postgres) и примените схему:
   ```bash
   psql "$DATABASE_URL" -f schema.sql
   ```
2. Скопируйте `.env.example` в `.env` и заполните `BOT_TOKEN`, `DATABASE_URL`, `ADMIN_TG_IDS`.
3. Установите зависимости и запустите один сервер — он отдаёт и `/api/*`, и статику из `public/`
   (раздача статики через FastAPI включена только для локального дев-режима, см. `api/index.py`):
   ```bash
   pip install -r requirements.txt uvicorn python-dotenv
   uvicorn api.index:app --reload --port 8000
   ```
   (переменные окружения должны быть выставлены в среде — например через `set -a; source .env; set +a` в bash
   или `Get-Content .env | ForEach-Object { ... }` в PowerShell, либо любой удобный dotenv-загрузчик)
4. Откройте `http://localhost:8000` — увидите интерфейс, но `Telegram.WebApp.initData` будет пустым
   (нет реального Telegram-контекста), поэтому `/api/me` ответит 401. Это нормально для проверки вёрстки/JS.
5. **Чтобы протестировать реально, как в Telegram** (с настоящим `initData`), локальный сервер нужно
   пробросить наружу по HTTPS — Telegram не откроет `http://localhost`:
   ```bash
   ngrok http 8000
   ```
   Полученный `https://xxxx.ngrok-free.app` временно укажите в @BotFather как URL кнопки меню
   (см. раздел ниже) — и открывайте бота в настоящем Telegram-клиенте. Так `initData` будет подписан
   настоящим Telegram и пройдёт валидацию в `api/auth.py`. После теста верните в BotFather боевой URL.

## Деплой на Vercel

```bash
npm i -g vercel   # если ещё не установлен
vercel login
vercel            # первый деплой, ответьте на вопросы мастера
vercel --prod     # деплой в прод
```

`vercel.json` уже настроен: `/api/*` → `api/index.py`, всё остальное → статика из `public/`.

### Переменные окружения в Vercel

Project Settings → Environment Variables:

| Переменная | Значение |
|---|---|
| `BOT_TOKEN` | токен от @BotFather |
| `DATABASE_URL` | pooled-connection строка Neon (хост с `-pooler`) |
| `ADMIN_TG_IDS` | telegram id первого администратора |
| `TRAINER_TG_IDS` | telegram id тренеров (опционально, дальше можно назначать из панели администратора) |
| `ALLOWED_ORIGIN` | можно оставить `*`, т.к. фронт и API на одном домене |
| `APP_URL` | URL вашего Vercel-деплоя — используется в кнопке под `/start` |
| `TELEGRAM_WEBHOOK_SECRET` | случайная строка, см. ниже |

## Настройка в @BotFather

1. `/newbot` (если бота ещё нет) → сохраните токен в `BOT_TOKEN`.
2. `/mybots` → выберите бота → **Bot Settings → Menu Button → Configure Menu Button**
   → укажите URL вашего Vercel-деплоя (например `https://hse-sport-centre.vercel.app`).
3. Там же можно настроить `/setdomain` для Web App, если планируете использовать
   `Telegram.Login` виджет отдельно (для чистого Mini App через меню-кнопку это не обязательно).
4. Откройте бота в Telegram → кнопка меню откроет Mini App.

## Ответ на /start

Бэкенд умеет отвечать на `/start` инструкцией с кнопкой, открывающей Mini App
(`api/routes_bot.py`), но Telegram должен знать, куда слать апдейты — для этого
**один раз** регистрируется webhook (выполнить после того, как заданы `APP_URL`
и `TELEGRAM_WEBHOOK_SECRET` в Vercel и сделан деплой):

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://<ваш-домен>/api/telegram/webhook" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

Проверить, что вебхук зарегистрирован:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

## Подводные камни

- **initData вне Telegram.** Если открыть `public/index.html` просто в браузере,
  `Telegram.WebApp.initData` будет пустой строкой, и `/api/me` ответит 401 — это ожидаемо,
  тестировать авторизацию нужно через реальный Telegram-клиент (кнопка меню бота или `t.me/<bot>?startapp=...`).
- **Свежесть initData.** Backend отклоняет `initData` старше 24 часов (`INIT_DATA_MAX_AGE` в `api/auth.py`) —
  если открыть когда-то сохранённую ссылку с initData, получите 401. Это нормально, initData каждый раз
  генерируется заново при открытии Mini App.
- **CORS.** На Vercel фронт и API на одном домене, кросс-доменных проблем не будет.
  Полностью открытый `allow_origins=["*"]` — ок для этого проекта, но если добавите куки/сессии — сузьте до конкретного домена.
- **Cold start / лимит 10 сек на бесплатном плане Vercel.** Каждый запрос к `api/index.py` создаёт новое
  соединение с Postgres (см. `api/db.py`) — используйте **pooled**-строку подключения Neon
  (хост с `-pooler`), иначе на холодном старте можно упереться в задержку установки TLS-сессии к БД
  и лимит по времени. Если понадобится больше 10 сек (например, тяжёлая генерация занятий на много
  недель вперёд для секции с большим количеством слотов) — либо увеличьте лимит на платном плане
  Vercel (`maxDuration` в `vercel.json`), либо разбейте операцию на несколько запросов с меньшим `weeks`.
- **Лимит размера бандла Python-функции на Vercel** (обычно 250 МБ распакованным). `psycopg2-binary` и `httpx`
  в этот лимит укладываются с большим запасом — но если начнёте добавлять тяжёлые библиотеки (pandas, numpy
  и т.п.), проверяйте размер через `vercel build` локально.
- **HTTPS обязателен.** Telegram Mini App открывается только по `https://` — Vercel выдаёт его автоматически,
  локальный `http://localhost` для теста внутри Telegram не подойдёт (нужен реальный домен или туннель типа ngrok).
- **Уведомления боту работают только в личных чатах, которые пользователь уже начал** (`/start` боту) —
  это гарантировано, так как открыть Mini App можно только через кнопку меню бота, а значит чат уже существует.

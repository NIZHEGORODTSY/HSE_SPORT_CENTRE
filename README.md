# HSE Sport Centre — Telegram Mini App

Запись студентов НИУ ВШЭ на спортивные секции: каталог секций, расписание,
запись/отмена, посещаемость по датам, новости (с публикацией и удалением). Роли: студент, тренер, администратор.

## Функционал

**Студент**
- Просматривает список секций с описанием, расписанием и количеством свободных мест
- Записывается на секцию и отменяет запись
- Видит свои записи и историю посещаемости по датам занятий в профиле
- Читает новости

**Тренер**
- Видит список своих секций
- Добавляет и удаляет еженедельные слоты расписания (день недели, время, место)
- Генерирует конкретные занятия с датами на несколько недель вперёд по расписанию
- Отменяет отдельное занятие
- Видит список студентов, записанных на секцию
- Отмечает посещаемость каждого студента по каждому занятию
- Публикует новости (с рассылкой уведомления всем студентам) и удаляет свои

**Администратор**
- Назначает и меняет роли пользователей (студент / тренер / администратор)
- Создаёт, редактирует и удаляет секции, назначает им тренера
- Обладает всеми правами тренера в отношении любой секции
- Публикует и удаляет любые новости

**Бот**
- Отвечает на `/start` инструкцией с кнопкой, открывающей Mini App
- Отправляет тренеру уведомление при записи/отмене записи студента на его секцию
- Рассылает студентам уведомление при публикации новости

## Стек

- Backend: FastAPI (Python), raw SQL через `psycopg2` (без ORM)
- Frontend: чистые HTML/CSS/JS, без фреймворков и сборщиков
- БД: Postgres (используется [Neon](https://neon.tech), pooled-connection)
- Деплой: Vercel (frontend — статика из `public/`, backend — serverless-функция `api/index.py`)
- Бот: Telegram Bot API через webhook (`api/routes_bot.py`)

## Структура

```
api/
  index.py            точка входа FastAPI: CORS, сборка роутеров, /api/health, /api/me,
                       раздача public/ для локального запуска
  auth.py              валидация Telegram initData, роли, upsert пользователя
  db.py                подключение к Postgres, query_all/query_one/execute
  bot_notify.py        отправка сообщений через Bot API (уведомления, broadcast)
  routes_bot.py        webhook: ответ на /start с кнопкой открытия Mini App
  routes_student.py    секции, запись/отмена, мои записи и посещаемость
  routes_trainer.py    расписание, генерация занятий, отметка посещаемости
  routes_admin.py      назначение ролей, CRUD секций
  routes_news.py       новости: список, публикация + broadcast студентам, удаление
public/
  index.html
  css/style.css
  js/api.js            обёртка над fetch с заголовком initData
  js/app.js             весь UI: рендер по ролям, переключение вкладок
schema.sql              DDL для Postgres
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
3. Установите зависимости и запустите сервер — он отдаёт и `/api/*`, и статику из `public/`
   (раздача статики через FastAPI включена только для локального запуска, см. `api/index.py`):
   ```bash
   pip install -r requirements.txt uvicorn python-dotenv
   uvicorn api.index:app --reload --port 8000
   ```
   `.env` подхватывается автоматически через `python-dotenv` (см. `api/index.py`).
4. `http://localhost:8000` отдаёт интерфейс; `Telegram.WebApp.initData` вне Telegram — пустая строка,
   поэтому `/api/me` отвечает 401.
5. Для проверки с настоящим `initData` локальный сервер нужно пробросить наружу по HTTPS:
   ```bash
   ngrok http 8000
   ```
   (ngrok v3 требует аккаунт и `ngrok config add-authtoken <token>` — токен на
   `dashboard.ngrok.com/get-started/your-authtoken`). Полученный `https://xxxx.ngrok-free.app`
   указывается в @BotFather как URL кнопки меню (см. раздел ниже) для теста в Telegram-клиенте.

## Деплой на Vercel

Через веб-интерфейс, без установки Node.js/CLI:

1. [vercel.com/new](https://vercel.com/new) → **Add New Project → Import Git Repository**
   → выберите репозиторий на GitHub.
2. Framework Preset — **Other** (конфигурация в `vercel.json`:
   `/api/*` → `api/index.py`, всё остальное → статика из `public/`).
3. До нажатия Deploy добавьте переменные окружения (см. таблицу ниже).
4. Deploy. При следующих `git push` в `main` Vercel передеплоивает автоматически.

Импорт приватного репозитория из GitHub-организации на бесплатном (Hobby) плане Vercel
недоступен без Pro — для этого репозиторий должен быть публичным или находиться в личном аккаунте.

Альтернатива — через CLI (нужен Node.js):
```bash
npm i -g vercel
vercel login
vercel            # первый деплой, ответьте на вопросы мастера
vercel --prod     # деплой в прод
```

### Переменные окружения в Vercel

Project Settings → Environment Variables:

| Переменная | Значение |
|---|---|
| `BOT_TOKEN` | токен от @BotFather |
| `DATABASE_URL` | pooled-connection строка Neon (хост с `-pooler`) |
| `ADMIN_TG_IDS` | telegram id первого администратора |
| `TRAINER_TG_IDS` | telegram id тренеров (опционально, дальше можно назначать из панели администратора) |
| `ALLOWED_ORIGIN` | `*`, т.к. фронт и API на одном домене |
| `APP_URL` | URL Vercel-деплоя — используется в кнопке под `/start` |
| `TELEGRAM_WEBHOOK_SECRET` | случайная строка, см. ниже |

## Настройка в @BotFather

1. `/newbot` (если бота ещё нет) → сохраните токен в `BOT_TOKEN`.
2. `/mybots` → выберите бота → главное меню → **Bot Settings → Menu Button → Configure Menu Button**
   (отдельный раздел от «Edit Bot», где редактируются имя/описание/аватар)
   → укажите URL Vercel-деплоя (например `https://hse-sport-centre.vercel.app`).
3. Там же настраивается `/setdomain` для Web App, если нужен `Telegram.Login` виджет отдельно
   от Mini App через меню-кнопку.
4. Кнопка меню в чате с ботом открывает Mini App.

## Ответ на /start

Бэкенд отвечает на `/start` инструкцией с inline-кнопкой, открывающей Mini App
(`api/routes_bot.py`). Telegram узнаёт, куда слать апдейты, через webhook —
регистрируется один раз после того, как заданы `APP_URL` и `TELEGRAM_WEBHOOK_SECRET`
в Vercel и сделан деплой:

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://<ваш-домен>/api/telegram/webhook" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

Проверка регистрации:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

При изменении `TELEGRAM_WEBHOOK_SECRET` после регистрации webhook — вызвать `setWebhook`
повторно с новым секретом, иначе вебхук будет отвечать 403 на реальные апдейты от Telegram.

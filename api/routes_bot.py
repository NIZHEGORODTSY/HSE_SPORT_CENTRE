import os

from fastapi import APIRouter, Header, HTTPException, Request

from api import bot_notify

router = APIRouter()

# Секрет из setWebhook — Telegram присылает его в каждом запросе, чтобы
# отличить настоящие апдейты от чужих POST-запросов на этот же URL.
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
APP_URL = os.environ.get("APP_URL", "")

WELCOME_TEXT = (
    "Привет! Это бот для записи на спортивные секции НИУ ВШЭ.\n\n"
    "Чтобы открыть приложение — нажмите кнопку меню рядом с полем ввода "
    "или кнопку ниже."
)


@router.post("/api/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(default="")):
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(403, "Invalid secret token")

    update = await request.json()
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = message.get("chat", {}).get("id")

    if chat_id and text.startswith("/start") and APP_URL:
        await bot_notify.send_message(
            chat_id,
            WELCOME_TEXT,
            reply_markup={"inline_keyboard": [[{"text": "Открыть Спорт ВШЭ", "web_app": {"url": APP_URL}}]]},
        )
    return {"ok": True}

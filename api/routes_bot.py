import os

from fastapi import APIRouter, Header, HTTPException, Request

from api import bot_notify

router = APIRouter()

# Секрет из setWebhook — Telegram присылает его в каждом запросе, чтобы
# отличить настоящие апдейты от чужих POST-запросов на этот же URL.
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
APP_URL = os.environ.get("APP_URL", "")

WELCOME_TEXT = (
    """🏅 Спорт ВШЭ — твой помощник в мире университетского спорта

Здесь можно:
• найти секцию по виду спорта, кампусу и времени
• записаться на занятие в один клик
• видеть своё расписание и историю посещений
• получать напоминания о занятиях и открытии записи
• отменить или перенести запись

Больше никаких гугл-форм, комментариев и потерянных сообщений в ВК. Все спортивные активности НИУ ВШЭ — в одном месте.

Нажми «Открыть Спорт ВШЭ», чтобы начать 👇"""
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

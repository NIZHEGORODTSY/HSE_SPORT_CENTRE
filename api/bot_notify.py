import asyncio
import os

import httpx

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


async def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    if not BOT_TOKEN:
        return
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            await client.post(API_URL, json=payload)
        except httpx.HTTPError:
            pass  # уведомление — best effort, не должно ронять основной запрос


async def broadcast(chat_ids: list[int], text: str) -> None:
    if not BOT_TOKEN or not chat_ids:
        return
    sem = asyncio.Semaphore(10)

    async def _send(chat_id: int):
        async with sem:
            await send_message(chat_id, text)

    await asyncio.gather(*(_send(cid) for cid in chat_ids))

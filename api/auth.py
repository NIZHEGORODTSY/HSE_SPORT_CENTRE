import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException

from api import db

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_TG_IDS = {int(x) for x in os.environ.get("ADMIN_TG_IDS", "").split(",") if x.strip()}
TRAINER_TG_IDS = {int(x) for x in os.environ.get("TRAINER_TG_IDS", "").split(",") if x.strip()}

INIT_DATA_MAX_AGE = 24 * 60 * 60  # initData считается действительной сутки


def validate_init_data(init_data: str) -> dict:
    """Проверка подписи Telegram WebApp initData (HMAC-SHA256)."""
    if not init_data:
        raise HTTPException(status_code=401, detail="No initData")

    parsed = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="No hash in initData")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid initData")

    auth_date = int(parsed.get("auth_date", "0"))
    if time.time() - auth_date > INIT_DATA_MAX_AGE:
        raise HTTPException(status_code=401, detail="initData expired")

    return parsed


def _resolve_role(tg_id: int, current_role: str | None) -> str:
    """Переменные окружения всегда могут повысить роль (бутстрап админов/тренеров),
    но никогда не понижают роль, уже выданную вручную через /api/admin."""
    if tg_id in ADMIN_TG_IDS:
        return "admin"
    if current_role == "admin":
        return "admin"
    if tg_id in TRAINER_TG_IDS:
        return "trainer"
    if current_role == "trainer":
        return "trainer"
    return current_role or "student"


def upsert_user(tg_user: dict) -> dict:
    tg_id = tg_user["id"]
    full_name = " ".join(filter(None, [tg_user.get("first_name"), tg_user.get("last_name")])) or "Без имени"
    username = tg_user.get("username")

    existing = db.query_one("SELECT * FROM users WHERE tg_id = %s", (tg_id,))
    role = _resolve_role(tg_id, existing["role"] if existing else None)

    if existing:
        return db.execute(
            """UPDATE users SET full_name = %s, username = %s, role = %s
               WHERE tg_id = %s RETURNING *""",
            (full_name, username, role, tg_id),
        )
    return db.execute(
        """INSERT INTO users (tg_id, role, full_name, username)
           VALUES (%s, %s, %s, %s) RETURNING *""",
        (tg_id, role, full_name, username),
    )


async def get_current_user(x_telegram_init_data: str = Header(default="")) -> dict:
    parsed = validate_init_data(x_telegram_init_data)
    tg_user = json.loads(parsed.get("user", "{}"))
    if "id" not in tg_user:
        raise HTTPException(status_code=401, detail="No user in initData")
    return upsert_user(tg_user)


def require_roles(*roles: str):
    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return user

    return dependency

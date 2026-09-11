from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api import bot_notify, db
from api.auth import get_current_user, require_roles

router = APIRouter()


@router.get("/api/news")
async def list_news(user: dict = Depends(get_current_user)):
    return db.query_all(
        """SELECT n.id, n.title, n.content, n.created_at, u.full_name AS author_name
           FROM news n LEFT JOIN users u ON u.id = n.author_id
           ORDER BY n.created_at DESC LIMIT 50"""
    )


class NewsIn(BaseModel):
    title: str
    content: str


@router.post("/api/news")
async def create_news(body: NewsIn, user: dict = Depends(require_roles("trainer", "admin"))):
    row = db.execute(
        "INSERT INTO news (title, content, author_id) VALUES (%s, %s, %s) RETURNING *",
        (body.title, body.content, user["id"]),
    )
    students = db.query_all("SELECT tg_id FROM users WHERE role = 'student'")
    await bot_notify.broadcast([s["tg_id"] for s in students], f"\U0001f4f0 {body.title}\n\n{body.content}")
    return row

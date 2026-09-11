from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api import db
from api.auth import require_roles

router = APIRouter()


@router.get("/api/admin/users")
async def list_users(role: str | None = None, user: dict = Depends(require_roles("admin"))):
    if role:
        return db.query_all("SELECT * FROM users WHERE role = %s ORDER BY full_name", (role,))
    return db.query_all("SELECT * FROM users ORDER BY full_name")


class RoleIn(BaseModel):
    role: str


@router.post("/api/admin/users/{user_id}/role")
async def set_role(user_id: int, body: RoleIn, admin: dict = Depends(require_roles("admin"))):
    if body.role not in ("student", "trainer", "admin"):
        raise HTTPException(400, "Недопустимая роль")
    row = db.execute("UPDATE users SET role = %s WHERE id = %s RETURNING *", (body.role, user_id))
    if not row:
        raise HTTPException(404, "Пользователь не найден")
    return row


@router.get("/api/admin/sections")
async def list_sections(user: dict = Depends(require_roles("admin"))):
    return db.query_all(
        """SELECT s.*, t.full_name AS trainer_name,
                  (SELECT COUNT(*) FROM enrollments e WHERE e.section_id = s.id) AS taken
           FROM sections s LEFT JOIN users t ON t.id = s.trainer_id
           ORDER BY s.name"""
    )


class SectionIn(BaseModel):
    name: str
    description: str = ""
    capacity: int
    trainer_id: int | None = None


@router.post("/api/admin/sections")
async def create_section(body: SectionIn, user: dict = Depends(require_roles("admin"))):
    return db.execute(
        """INSERT INTO sections (name, description, capacity, trainer_id)
           VALUES (%s, %s, %s, %s) RETURNING *""",
        (body.name, body.description, body.capacity, body.trainer_id),
    )


@router.put("/api/admin/sections/{section_id}")
async def update_section(section_id: int, body: SectionIn, user: dict = Depends(require_roles("admin"))):
    row = db.execute(
        """UPDATE sections SET name = %s, description = %s, capacity = %s, trainer_id = %s
           WHERE id = %s RETURNING *""",
        (body.name, body.description, body.capacity, body.trainer_id, section_id),
    )
    if not row:
        raise HTTPException(404, "Секция не найдена")
    return row


@router.delete("/api/admin/sections/{section_id}")
async def delete_section(section_id: int, user: dict = Depends(require_roles("admin"))):
    row = db.execute("DELETE FROM sections WHERE id = %s RETURNING id", (section_id,))
    if not row:
        raise HTTPException(404, "Секция не найдена")
    return {"ok": True}

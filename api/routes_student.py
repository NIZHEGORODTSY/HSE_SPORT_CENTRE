from fastapi import APIRouter, Depends, HTTPException

from api import bot_notify, db
from api.auth import get_current_user

router = APIRouter()


@router.get("/api/sections")
async def list_sections(user: dict = Depends(get_current_user)):
    sections = db.query_all(
        """SELECT s.id, s.name, s.description, s.capacity, t.full_name AS trainer_name,
                  (SELECT COUNT(*) FROM enrollments e WHERE e.section_id = s.id) AS taken,
                  EXISTS(
                      SELECT 1 FROM enrollments e
                      WHERE e.section_id = s.id AND e.student_id = %s
                  ) AS enrolled
           FROM sections s
           LEFT JOIN users t ON t.id = s.trainer_id
           ORDER BY s.name""",
        (user["id"],),
    )
    for s in sections:
        s["schedule"] = db.query_all(
            """SELECT weekday, start_time, end_time, location
               FROM schedule_slots WHERE section_id = %s ORDER BY weekday, start_time""",
            (s["id"],),
        )
    return sections


@router.post("/api/sections/{section_id}/enroll")
async def enroll(section_id: int, user: dict = Depends(get_current_user)):
    section = db.query_one("SELECT * FROM sections WHERE id = %s", (section_id,))
    if not section:
        raise HTTPException(404, "Секция не найдена")

    taken = db.query_one("SELECT COUNT(*) AS c FROM enrollments WHERE section_id = %s", (section_id,))["c"]
    if taken >= section["capacity"]:
        raise HTTPException(400, "Нет свободных мест")

    already = db.query_one(
        "SELECT 1 FROM enrollments WHERE section_id = %s AND student_id = %s", (section_id, user["id"])
    )
    if already:
        raise HTTPException(400, "Вы уже записаны")

    db.execute("INSERT INTO enrollments (section_id, student_id) VALUES (%s, %s)", (section_id, user["id"]))

    if section["trainer_id"]:
        trainer = db.query_one("SELECT tg_id FROM users WHERE id = %s", (section["trainer_id"],))
        if trainer:
            await bot_notify.send_message(
                trainer["tg_id"], f"Студент {user['full_name']} записался на секцию «{section['name']}»"
            )
    return {"ok": True}


@router.delete("/api/sections/{section_id}/enroll")
async def cancel_enrollment(section_id: int, user: dict = Depends(get_current_user)):
    row = db.execute(
        "DELETE FROM enrollments WHERE section_id = %s AND student_id = %s RETURNING id",
        (section_id, user["id"]),
    )
    if not row:
        raise HTTPException(404, "Запись не найдена")

    section = db.query_one("SELECT * FROM sections WHERE id = %s", (section_id,))
    if section and section["trainer_id"]:
        trainer = db.query_one("SELECT tg_id FROM users WHERE id = %s", (section["trainer_id"],))
        if trainer:
            await bot_notify.send_message(
                trainer["tg_id"], f"Студент {user['full_name']} отменил запись на секцию «{section['name']}»"
            )
    return {"ok": True}


@router.get("/api/my/enrollments")
async def my_enrollments(user: dict = Depends(get_current_user)):
    return db.query_all(
        """SELECT s.id, s.name, s.description, e.created_at
           FROM enrollments e JOIN sections s ON s.id = e.section_id
           WHERE e.student_id = %s ORDER BY e.created_at DESC""",
        (user["id"],),
    )


@router.get("/api/my/attendance")
async def my_attendance(user: dict = Depends(get_current_user)):
    return db.query_all(
        """SELECT se.session_date, se.start_time, s.name AS section_name, a.status
           FROM attendance a
           JOIN sessions se ON se.id = a.session_id
           JOIN sections s ON s.id = se.section_id
           WHERE a.student_id = %s
           ORDER BY se.session_date DESC""",
        (user["id"],),
    )

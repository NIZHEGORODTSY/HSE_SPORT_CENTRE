from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api import db
from api.auth import require_roles

router = APIRouter()


def _assert_owns_section(section_id: int, user: dict) -> dict:
    section = db.query_one("SELECT * FROM sections WHERE id = %s", (section_id,))
    if not section:
        raise HTTPException(404, "Секция не найдена")
    if user["role"] != "admin" and section["trainer_id"] != user["id"]:
        raise HTTPException(403, "Это не ваша секция")
    return section


@router.get("/api/trainer/sections")
async def my_sections(user: dict = Depends(require_roles("trainer", "admin"))):
    return db.query_all(
        """SELECT s.*, (SELECT COUNT(*) FROM enrollments e WHERE e.section_id = s.id) AS taken
           FROM sections s WHERE s.trainer_id = %s ORDER BY s.name""",
        (user["id"],),
    )


class SlotIn(BaseModel):
    weekday: int
    start_time: str
    end_time: str
    location: str = ""


@router.post("/api/trainer/sections/{section_id}/schedule")
async def add_slot(section_id: int, slot: SlotIn, user: dict = Depends(require_roles("trainer", "admin"))):
    _assert_owns_section(section_id, user)
    if not (0 <= slot.weekday <= 6):
        raise HTTPException(400, "weekday должен быть от 0 (понедельник) до 6 (воскресенье)")
    return db.execute(
        """INSERT INTO schedule_slots (section_id, weekday, start_time, end_time, location)
           VALUES (%s, %s, %s, %s, %s) RETURNING *""",
        (section_id, slot.weekday, slot.start_time, slot.end_time, slot.location),
    )


@router.delete("/api/trainer/schedule/{slot_id}")
async def delete_slot(slot_id: int, user: dict = Depends(require_roles("trainer", "admin"))):
    slot = db.query_one("SELECT * FROM schedule_slots WHERE id = %s", (slot_id,))
    if not slot:
        raise HTTPException(404, "Слот не найден")
    _assert_owns_section(slot["section_id"], user)
    db.execute("DELETE FROM schedule_slots WHERE id = %s", (slot_id,))
    return {"ok": True}


class GenerateIn(BaseModel):
    weeks: int = 4


@router.post("/api/trainer/sections/{section_id}/sessions/generate")
async def generate_sessions(
    section_id: int, body: GenerateIn, user: dict = Depends(require_roles("trainer", "admin"))
):
    _assert_owns_section(section_id, user)
    slots = db.query_all("SELECT * FROM schedule_slots WHERE section_id = %s", (section_id,))
    if not slots:
        raise HTTPException(400, "У секции нет расписания — сначала добавьте слоты")

    today = date.today()
    created = 0
    for i in range(body.weeks * 7):
        d = today + timedelta(days=i)
        for slot in slots:
            if d.weekday() == slot["weekday"]:
                row = db.execute(
                    """INSERT INTO sessions (section_id, slot_id, session_date, start_time, end_time)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (section_id, session_date, start_time) DO NOTHING
                       RETURNING id""",
                    (section_id, slot["id"], d, slot["start_time"], slot["end_time"]),
                )
                if row:
                    created += 1
    return {"created": created}


@router.get("/api/trainer/sections/{section_id}/sessions")
async def list_sessions(section_id: int, user: dict = Depends(require_roles("trainer", "admin"))):
    _assert_owns_section(section_id, user)
    return db.query_all(
        "SELECT * FROM sessions WHERE section_id = %s ORDER BY session_date, start_time", (section_id,)
    )


@router.delete("/api/trainer/sessions/{session_id}")
async def cancel_session(session_id: int, user: dict = Depends(require_roles("trainer", "admin"))):
    session = db.query_one("SELECT * FROM sessions WHERE id = %s", (session_id,))
    if not session:
        raise HTTPException(404, "Занятие не найдено")
    _assert_owns_section(session["section_id"], user)
    db.execute("UPDATE sessions SET status = 'cancelled' WHERE id = %s", (session_id,))
    return {"ok": True}


@router.get("/api/trainer/sections/{section_id}/students")
async def section_students(section_id: int, user: dict = Depends(require_roles("trainer", "admin"))):
    _assert_owns_section(section_id, user)
    return db.query_all(
        """SELECT u.id, u.full_name, u.username, e.created_at AS enrolled_at,
                  sl.weekday, sl.start_time, sl.end_time
           FROM enrollments e
           JOIN users u ON u.id = e.student_id
           LEFT JOIN schedule_slots sl ON sl.id = e.slot_id
           WHERE e.section_id = %s ORDER BY u.full_name""",
        (section_id,),
    )


@router.get("/api/trainer/sessions/{session_id}/attendance")
async def get_attendance(session_id: int, user: dict = Depends(require_roles("trainer", "admin"))):
    session = db.query_one("SELECT * FROM sessions WHERE id = %s", (session_id,))
    if not session:
        raise HTTPException(404, "Занятие не найдено")
    section = _assert_owns_section(session["section_id"], user)

    students = db.query_all(
        """SELECT u.id AS student_id, u.full_name, u.username
           FROM enrollments e JOIN users u ON u.id = e.student_id
           WHERE e.section_id = %s AND (e.slot_id = %s OR e.slot_id IS NULL)
           ORDER BY u.full_name""",
        (section["id"], session["slot_id"]),
    )
    marks = {
        row["student_id"]: row["status"]
        for row in db.query_all("SELECT student_id, status FROM attendance WHERE session_id = %s", (session_id,))
    }
    for s in students:
        s["status"] = marks.get(s["student_id"], "unmarked")
    return {"session": session, "students": students}


class AttendanceIn(BaseModel):
    marks: dict[int, str]


@router.post("/api/trainer/sessions/{session_id}/attendance")
async def set_attendance(
    session_id: int, body: AttendanceIn, user: dict = Depends(require_roles("trainer", "admin"))
):
    session = db.query_one("SELECT * FROM sessions WHERE id = %s", (session_id,))
    if not session:
        raise HTTPException(404, "Занятие не найдено")
    _assert_owns_section(session["section_id"], user)

    for student_id, status in body.marks.items():
        if status not in ("present", "absent", "unmarked"):
            raise HTTPException(400, f"Некорректный статус: {status}")
        db.execute(
            """INSERT INTO attendance (session_id, student_id, status, marked_at)
               VALUES (%s, %s, %s, now())
               ON CONFLICT (session_id, student_id)
               DO UPDATE SET status = EXCLUDED.status, marked_at = now()""",
            (session_id, student_id, status),
        )
    return {"ok": True}

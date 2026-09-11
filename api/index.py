import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()  # локальная разработка: подхватывает .env; на Vercel файла нет, вызов no-op
except ImportError:
    pass

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import routes_admin, routes_news, routes_student, routes_trainer
from api.auth import get_current_user

app = FastAPI(title="HSE Sport Centre API")

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN] if ALLOWED_ORIGIN != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/me")
async def me(user: dict = Depends(get_current_user)):
    return user


app.include_router(routes_student.router)
app.include_router(routes_trainer.router)
app.include_router(routes_admin.router)
app.include_router(routes_news.router)

# Раздача public/ нужна только для локального запуска (uvicorn api.index:app).
# На Vercel статику отдаёт vercel.json, до этой функции такие запросы не доходят.
_PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
if _PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=_PUBLIC_DIR, html=True), name="public")

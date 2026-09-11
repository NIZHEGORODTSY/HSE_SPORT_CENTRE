import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

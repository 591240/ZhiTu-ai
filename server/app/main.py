from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.config import settings, BASE_DIR
from app.services.template_service import template_service
from app.routers import auth, plan, trip, template, chat, service, membership, collection, ocr, user, sms, distribution, track, ticket, map, ota

# 更新文档：项目名统一为「知途 AI 旅行」


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await template_service.seed()
    yield


app = FastAPI(title="知途 AI 旅行 API", version="1.0.0", lifespan=lifespan)

# 静态资源（头像上传后永久可访问）
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "avatars").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, plan, trip, template, chat, service, membership, collection, ocr, user, sms, distribution, track, ticket, map, ota):
    app.include_router(r.router)


@app.get("/")
async def root():
    return {"code": 0, "message": "知途 AI 旅行 API 运行中", "data": None}


@app.get("/api/health")
async def health():
    return {"status": "ok"}

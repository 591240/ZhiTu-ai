from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.services.template_service import template_service
from app.routers import auth, plan, trip, template, chat, service, membership, collection, ocr, user, sms, distribution, track, ticket, map, ota

# 更新文档：项目名统一为「知途 AI 旅行」


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await template_service.seed()
    yield


app = FastAPI(title="知途 AI 旅行 API", version="1.0.0", lifespan=lifespan)

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

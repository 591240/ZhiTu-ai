from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.config import settings, BASE_DIR
from app.services.template_service import template_service
from app.routers import auth, plan, trip, template, chat, service, membership, collection, ocr, user, sms, distribution, track, ticket, map, ota, kb

# httpx 会把完整请求 URL 打进 INFO 日志，而微信接口的 URL 里带 access_token、
# 查询参数里还可能带 AppSecret——压到 WARNING，避免凭据落到日志里。
logging.getLogger("httpx").setLevel(logging.WARNING)

# 更新文档：项目名统一为「知途 AI 旅行」


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await template_service.seed()
    yield


# 安全加固：上线前关闭自动生成的接口文档（/docs、/redoc、/openapi.json），
# 避免接口结构被公开扫描。开发调试时可临时把三个 url 改回默认（去掉 =None）。
app = FastAPI(
    title="知途 AI 旅行 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# 静态资源（头像上传后永久可访问）
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "avatars").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 开发态放行的来源：本机、回环、真机联调用的局域网段。
DEV_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?$"


def build_cors_kwargs(cfg) -> dict:
    """单独抽成函数：否则 production 分支要换环境变量重启进程才能验证，测试就覆盖不到。"""
    # 裸 "*" 与 allow_credentials=True 是浏览器不接受的组合；本项目没有网页端，
    # 通配来源没有任何用处，直接从白名单里剔掉，防止误配成 ["*"]。
    origins = [o for o in cfg.cors_origin_list() if o != "*"]
    kwargs = {
        "allow_origins": origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if cfg.app_env != "production":
        kwargs["allow_origin_regex"] = DEV_ORIGIN_REGEX
    return kwargs


app.add_middleware(CORSMiddleware, **build_cors_kwargs(settings))

for r in (auth, plan, trip, template, chat, service, membership, collection, ocr, user, sms, distribution, track, ticket, map, ota, kb):
    app.include_router(r.router)


@app.get("/")
async def root():
    return {"code": 0, "message": "知途 AI 旅行 API 运行中", "data": None}


@app.get("/api/health")
async def health():
    return {"status": "ok"}

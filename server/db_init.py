"""同步建表脚本：在真实 MySQL 上创建全部表 + 写入模板种子数据。

用法（在 server 目录下）：
    venv/Scripts/python.exe db_init.py

说明：
- 凭据从 `app.config.settings` 读（pydantic-settings 自己会加载 .env），
  不再依赖 python-dotenv——那个包没写进 requirements.txt，新环境一跑就 ImportError。
- MySQL 需要同步驱动 pymysql，这里**按需导入**：用 SQLite 时不装也能跑。
- 幂等：表已存在则跳过；模板已有数据则不重复插入。
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# 确保所有 model 注册到 Base.metadata
from app.database import Base
from app.models import Template  # noqa: F401
from app.config import settings


def _sync_url() -> str:
    url = settings.database_url
    if url.startswith("mysql+aiomysql://"):
        try:
            import pymysql  # noqa: F401
        except ImportError as e:
            raise SystemExit(
                "连 MySQL 需要同步驱动：pip install pymysql\n"
                f"原始错误: {e}"
            )
        return url.replace("mysql+aiomysql://", "mysql+pymysql://")
    if url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite+aiosqlite:///", "sqlite:///")
    return url


SYNC_URL = _sync_url()
print(f"连接: {SYNC_URL.split('@')[-1] if '@' in SYNC_URL else SYNC_URL}")

engine = create_engine(SYNC_URL, echo=False)

print("正在创建表...")
Base.metadata.create_all(engine)

# SHOW TABLES 是 MySQL 专有语法，用 inspect 才能同时兼容 SQLite / MySQL
tables = sorted(inspect(engine).get_table_names())
print(f"\n✅ 建表完成！共 {len(tables)} 张表:")
for t in tables:
    print(f"  - {t}")

# 模板种子数据
TEMPLATES = [
    ("杭州2日经典游", "杭州", 2, 8, "popular", "🏞️"),
    ("成都3日小众深度游", "成都", 3, 10, "niche", "🐼"),
    ("苏州1日园林精华游", "苏州", 1, 4, "popular", "🌿"),
    ("西安3日古都文化游", "西安", 3, 12, "popular", "🏯"),
    ("厦门2日文艺漫游", "厦门", 2, 7, "niche", "🌊"),
]

with Session(bind=engine) as s:
    existing = {r[0] for r in s.query(Template.title).all()}
    if existing:
        print(f"\n模板已有 {len(existing)} 条，跳过种子数据")
    else:
        from app.services.plan_service import gen_trip

        for title, city, days, spots, rt, cover in TEMPLATES:
            trip = gen_trip({"city": city, "days": days, "route_type": rt})
            s.add(Template(
                title=title, city=city, days=days, spots_count=spots,
                route_type=rt, cover=cover, content=trip.get("content", {}), uses=0,
            ))
        s.commit()
        print(f"\n已插入 {len(TEMPLATES)} 条模板种子数据")

print("\n✅ 种子数据就绪，后端可启动！")

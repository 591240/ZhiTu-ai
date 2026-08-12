"""同步建表脚本：在真实 MySQL 上创建全部表"""
import os
import sys
import json

# 加载 .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "")
# 把 aiomysql 替换为 pymysql（同步驱动）
SYNC_URL = DATABASE_URL.replace("mysql+aiomysql://", "mysql+pymysql://")
print(f"连接: {SYNC_URL.split('@')[1] if '@' in SYNC_URL else SYNC_URL}")

engine = create_engine(SYNC_URL, echo=False)

# 建表（使用 models 里的 Base）
from app.database import Base
from app.models import *  # noqa: F401,F403 – 确保所有 model 被注册到 Base.metadata

print("正在创建表...")
Base.metadata.create_all(engine)

# 验证
with engine.connect() as conn:
    result = conn.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result.fetchall()]
    print(f"\n✅ 建表完成！共 {len(tables)} 张表:")
    for t in sorted(tables):
        print(f"  - {t}")

    # 插入种子数据（城市 + 服务链接）
    cities = [
        ("杭州", "浙江", "hangzhou", 1),
        ("成都", "四川", "chengdu", 1),
        ("北京", "北京", "beijing", 1),
        ("上海", "上海", "shanghai", 1),
        ("西安", "陕西", "xian", 1),
        ("苏州", "江苏", "suzhou", 1),
        ("重庆", "重庆", "chongqing", 1),
        ("厦门", "福建", "xiamen", 1),
        ("青岛", "山东", "qingdao", 0),
        ("大理", "云南", "dali", 0),
        ("长沙", "湖南", "changsha", 0),
        ("南京", "江苏", "nanjing", 0),
    ]
    services = [
        ("高德导航", "", "/pages/index/index", "🧭"),
        ("滴滴出行", "", "/pages/index/index", "🚕"),
        ("携程酒店", "", "/pages/index/index", "🏨"),
        ("大众点评", "", "/pages/index/index", "🍜"),
        ("12306火车票", "", "/pages/index/index", "🚄"),
        ("飞猪机票", "", "/pages/index/index", "✈️"),
    ]

    existing_cities = {r[0] for r in conn.execute(text("SELECT name FROM cities")).fetchall()}
    if not existing_cities:
        for name, prov, py, hot in cities:
            conn.execute(
                text("INSERT INTO cities (name, province, pinyin, is_hot) VALUES (:n, :p, :py, :h)"),
                {"n": name, "p": prov, "py": py, "h": hot}
            )
        print(f"  已插入 {len(cities)} 条城市种子数据")

    existing_svcs = {r[0] for r in conn.execute(text("SELECT name FROM service_links")).fetchall()}
    if not existing_svcs:
        for name, aid, path, icon in services:
            conn.execute(
                text("INSERT INTO service_links (name, app_id, path, icon) VALUES (:n, :a, :p, :i)"),
                {"n": name, "a": aid, "p": path, "i": icon}
            )
        print(f"  已插入 {len(services)} 条服务链接种子数据")

    # 插入模板种子数据（用 ORM 自动处理默认值）
    from sqlalchemy.orm import Session
    templates = [
        ("杭州2日经典游", "杭州", 2, 8, "popular", "🏞️"),
        ("成都3日小众深度游", "成都", 3, 10, "niche", "🐼"),
        ("苏州1日园林精华游", "苏州", 1, 4, "popular", "🌿"),
        ("西安3日古都文化游", "西安", 3, 12, "popular", "🏛️"),
        ("厦门2日文艺漫游", "厦门", 2, 7, "niche", "🌊"),
    ]
    existing_tpls = {r[0] for r in conn.execute(text("SELECT title FROM templates")).fetchall()}
    if not existing_tpls:
        from app.services.plan_service import gen_trip
        orm_session = Session(bind=engine)
        for title, city, days, spots, rt, cover in templates:
            trip = gen_trip({"city": city, "days": days, "route_type": rt})
            tpl = Template(
                title=title, city=city, days=days, spots_count=spots,
                route_type=rt, cover=cover, content=trip.get("content", {}), uses=0
            )
            orm_session.add(tpl)
        orm_session.commit()
        orm_session.close()
        print(f"  已插入 {len(templates)} 条模板种子数据")

    conn.commit()
    print("\n✅ 种子数据就绪，后端可启动！")

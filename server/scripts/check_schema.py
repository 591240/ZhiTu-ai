#!/usr/bin/env python
"""Schema 体检：对比 models 定义与数据库实际结构，报告缺表 / 缺列 / 缺唯一索引。

为什么需要它：项目靠 `Base.metadata.create_all()` 建表，它**只会建不存在的表，
不会给已存在的表加列或加约束**。历史上因此出过两次事故——
`invite_code` 字段和 `collections` 唯一索引都是"代码改了但旧库没有"。
这个脚本把这类漂移一次性暴露出来，不用等线上报错才发现。

只读，不修改任何数据。退出码 0 = 一致，1 = 有漂移。

用法（在 server 目录下）：
    venv/Scripts/python.exe scripts/check_schema.py
"""
import asyncio
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.models import Base  # noqa: E402  (确保所有 model 已注册)


def _actual_tables(conn) -> set[str]:
    if conn.dialect.name == "sqlite":
        rows = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )).fetchall()
        return {str(r[0]).lower() for r in rows}
    rows = conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
    )).fetchall()
    return {str(r[0]).lower() for r in rows}


def _actual_columns(conn, table: str) -> dict[str, str]:
    if conn.dialect.name == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
        # 行结构: (cid, name, type, notnull, dflt_value, pk)
        return {str(r[1]).lower(): str(r[2] or "").upper() for r in rows}
    rows = conn.execute(text(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = :t"
    ), {"t": table}).mappings().all()
    return {str(r["column_name"]).lower(): str(r["column_type"] or "").upper() for r in rows}


def _unique_indexes(conn, table: str) -> list[set[str]]:
    """返回该表所有唯一约束的列集合列表。"""
    if conn.dialect.name == "sqlite":
        out: list[set[str]] = []
        for row in conn.execute(text(f"PRAGMA index_list('{table}')")).fetchall():
            name, unique = row[1], row[2]
            if not unique:
                continue
            cols = conn.execute(text(f"PRAGMA index_info('{name}')")).fetchall()
            out.append({str(c[2]).lower() for c in cols})
        return out

    rows = conn.execute(text(f"SHOW INDEX FROM {table}")).mappings().all()
    by_name: dict[str, set[str]] = {}
    uniq_names: set[str] = set()
    for r in rows:
        key = str(r.get("Key_name") or "")
        by_name.setdefault(key, set()).add(str(r.get("Column_name") or "").lower())
        if int(r.get("Non_unique") or 0) == 0:
            uniq_names.add(key)
    return [by_name.get(n, set()) for n in uniq_names]


def _check_sync(conn):
    problems: list[str] = []
    warns: list[str] = []
    tables = _actual_tables(conn)

    for table in Base.metadata.tables.values():
        if table.name.lower() not in tables:
            problems.append(f"缺表 {table.name} —— 跑一次 db_init.py，或等启动时 create_all")
            continue

        actual = _actual_columns(conn, table.name)
        want_cols = {c.name.lower() for c in table.columns}

        for c in sorted(want_cols - set(actual)):
            problems.append(f"{table.name} 缺列 {c}")
        for c in sorted(set(actual) - want_cols):
            warns.append(f"{table.name} 有多余列 {c}（库里有、模型没定义，可能是历史遗留）")

        # 唯一约束比对（按列集合，不管索引名）
        want_unique: list[set[str]] = []
        for con in table.constraints:
            if con.__class__.__name__ == "UniqueConstraint":
                cols = {c.name.lower() for c in getattr(con, "columns", [])}
                if cols:
                    want_unique.append(cols)
        for col in table.columns:
            if col.unique and not col.primary_key:
                want_unique.append({col.name.lower()})

        if want_unique:
            have = _unique_indexes(conn, table.name)
            for cols in want_unique:
                if not any(cols == h for h in have):
                    problems.append(
                        f"{table.name} 缺唯一约束 ({', '.join(sorted(cols))}) "
                        f"—— create_all 不会给旧表加约束，需手工迁移"
                    )

    print(f"数据库: {engine.url.render_as_string(hide_password=True)}")
    print(f"模型定义 {len(Base.metadata.tables)} 张表，实际 {len(tables)} 张表\n")

    if problems:
        print(f"❌ 发现 {len(problems)} 处漂移：")
        for p in problems:
            print(f"  - {p}")
    if warns:
        print(f"\n⚠️  {len(warns)} 处提醒：")
        for w in warns:
            print(f"  - {w}")
    if not problems and not warns:
        print("✅ 数据库结构与模型完全一致")
    elif not problems:
        print("\n结论: 无阻塞性问题（提醒项可自行判断）")
    else:
        print("\n结论: 需要处理上面的漂移项")

    return 1 if problems else 0


async def check() -> int:
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(_check_sync)
    except Exception as e:
        # 连不上库时给一句人话，而不是一整页 asyncio traceback
        print(f"❌ 连不上数据库：{type(e).__name__}: {e}")
        print(f"   连接串: {engine.url.render_as_string(hide_password=True)}")
        print("   检查：数据库是否已启动、DATABASE_URL 是否正确、凭据是否有效。")
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))

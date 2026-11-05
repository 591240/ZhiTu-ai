"""迁移 001：为 collections 表补 (user_id, template_id) 唯一索引。

背景：`models.Collection` 上的 `UniqueConstraint` 只对**新建库**生效——
`Base.metadata.create_all()` 不会给已存在的表加约束。2026-10-23 之前的库里
这张表没有唯一索引，并发重复点收藏会插入多条记录。

幂等：重复执行安全（先查重删重，再判断索引是否已存在）。

用法（在 server 目录下）：
    venv/Scripts/python.exe scripts/migrations/001_collection_unique.py
"""
import asyncio
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVER_DIR))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

INDEX_NAME = "uq_collection_user_table"
TABLE = "collections"
COLS = ("user_id", "template_id")


async def _has_unique_index(conn) -> bool:
    """按「列集合」判断唯一约束是否存在，而不是按索引名——不同库生成的名字可能不一致。

    注意：不能对 AsyncConnection 用 inspect()（SQLAlchemy 会抛 NoInspectionAvailable），
    这里直接按 dialect 查系统表。
    """
    dialect = conn.dialect.name
    if dialect == "sqlite":
        rows = (await conn.execute(
            text(f"PRAGMA index_list('{TABLE}')"))).fetchall()
        # 行结构: (seq, name, unique, origin, partial)
        for _, name, unique, *_ in rows:
            if not unique:
                continue
            cols = (await conn.execute(
                text(f"PRAGMA index_info('{name}')"))).fetchall()
            if {str(c[2]).lower() for c in cols} == set(COLS):
                return True
        return False

    # MySQL / MariaDB
    rows = (await conn.execute(text(f"SHOW INDEX FROM {TABLE}"))).mappings().all()
    by_name: dict[str, set[str]] = {}
    unique_names: set[str] = set()
    for r in rows:
        key = str(r.get("Key_name") or "")
        by_name.setdefault(key, set()).add(str(r.get("Column_name") or "").lower())
        if int(r.get("Non_unique") or 0) == 0:
            unique_names.add(key)
    return any(by_name.get(n) == set(COLS) for n in unique_names)


async def migrate() -> int:
    async with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            tables = (await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"), {"t": TABLE}
            )).fetchall()
        else:
            tables = (await conn.execute(
                text("SELECT table_name FROM information_schema.tables "
                     "WHERE table_schema = DATABASE() AND table_name = :t"), {"t": TABLE}
            )).fetchall()

        if not tables:
            print(f"{TABLE} 表不存在，跳过（首次启动会自动建表，约束已含在模型里）")
            return 0

        # 1) 删掉历史重复收藏，只保留每个 (user_id, template_id) 最早的一条
        dup = (await conn.execute(text(
            f"SELECT user_id, template_id, COUNT(*) c, MIN(id) keep_id "
            f"FROM {TABLE} GROUP BY user_id, template_id HAVING c > 1"
        ))).fetchall()
        removed = 0
        for user_id, template_id, cnt, keep_id in dup:
            res = await conn.execute(
                text(f"DELETE FROM {TABLE} WHERE user_id = :u AND template_id = :t AND id <> :keep"),
                {"u": user_id, "t": template_id, "keep": keep_id},
            )
            removed += res.rowcount or 0
        if dup:
            print(f"清理重复收藏 {len(dup)} 组，删除 {removed} 条冗余记录")

        # 2) 补唯一索引
        if await _has_unique_index(conn):
            print(f"{TABLE} 已有 ({', '.join(COLS)}) 唯一约束，跳过")
            return 0

        if engine.dialect.name == "sqlite":
            # SQLite 不能 ALTER ADD CONSTRAINT，但 CREATE UNIQUE INDEX 等效
            await conn.execute(text(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} ON {TABLE} ({', '.join(COLS)})"
            ))
        else:
            await conn.execute(text(
                f"ALTER TABLE {TABLE} ADD UNIQUE KEY {INDEX_NAME} ({', '.join(COLS)})"
            ))
        print(f"{TABLE} 已添加 ({', '.join(COLS)}) 唯一索引")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(migrate()))

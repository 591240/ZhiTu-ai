"""迁移：新增分销佣金与数据埋点所需结构。

- users 表加 invite_code / invited_by 字段（已存在则跳过）
- 新建 distribution_records / events 表（已存在则跳过）
- 为没有 invite_code 的存量用户生成邀请码
"""
import asyncio
import random
import string

from sqlalchemy import text

from app.database import engine
from app.models import Base, User
from app.config import settings


def gen_code(n=settings.invite_code_len):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=n))


async def run():
    async with engine.begin() as conn:
        # 1) users 加字段
        cols = await conn.execute(text(
            "select column_name from information_schema.columns "
            "where table_schema = database() and table_name = 'users'"
        ))
        existing = {r[0] for r in cols.fetchall()}
        for col, ddl in (
            ("invite_code", "varchar(32)"),
            ("invited_by", "int"),
        ):
            if col not in existing:
                await conn.execute(text(f"alter table users add column {col} {ddl}"))
                print(f"  + users.{col}")
            else:
                print(f"  = users.{col} 已存在")

        # 2) 建新表
        await conn.run_sync(Base.metadata.create_all)
        print("  + distribution_records / events 表已就绪")

    # 3) 回填邀请码（保证唯一）
    async with engine.begin() as conn:
        rows = (await conn.execute(text(
            "select id from users where invite_code is null or invite_code = ''"
        ))).fetchall()
        for (uid,) in rows:
            async with engine.begin() as c2:
                # 碰撞重试
                for _ in range(10):
                    code = gen_code()
                    dup = (await c2.execute(text(
                        "select 1 from users where invite_code = :c"
                    ), {"c": code})).fetchone()
                    if not dup:
                        await c2.execute(text(
                            "update users set invite_code = :c where id = :u"
                        ), {"c": code, "u": uid})
                        break
        print(f"  ~ 回填邀请码 {len(rows)} 条")


if __name__ == "__main__":
    asyncio.run(run())
    print("迁移完成")

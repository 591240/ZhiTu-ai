"""迁移：为 users 表添加 is_active 字段；新增 feedbacks 表。"""
import asyncio
from sqlalchemy import text
from app.database import engine


async def migrate():
    async with engine.begin() as conn:
        # 添加 is_active 字段（如已存在则忽略）
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1"))
            print("users.is_active 添加成功")
        except Exception as e:
            print(f"users.is_active 可能已存在: {e}")

        # 创建 feedbacks 表
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    content TEXT NOT NULL,
                    contact VARCHAR(64) DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            print("feedbacks 表创建成功")
        except Exception as e:
            print(f"feedbacks 表可能已存在: {e}")


if __name__ == "__main__":
    asyncio.run(migrate())

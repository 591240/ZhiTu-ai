"""pytest 全局夹具。

关键约定：测试一律不许连 MySQL——那是共享演示库，脏数据删不干净。
这里在导入任何 app.* 之前把 DATABASE_URL / REDIS_URL / 变现开关 覆盖成临时 SQLite，
pydantic-settings 的环境变量优先级高于 .env 文件，所以覆盖生效。
"""
import os
import tempfile
from pathlib import Path

_TMP_DB = Path(tempfile.gettempdir()) / "zhitu_pytest.db"
_TMP_DB.unlink(missing_ok=True)

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB.as_posix()}"
os.environ["REDIS_URL"] = ""
# 默认断开向量库：开发机 .env 里若填了 KB_MILVUS_URI（内嵌 .db 文件），
# 不让用例误读写它；需要 Milvus 的用例走下面的 tmp_index 夹具指向自己的临时库。
# 注意变量名带 KB_ 前缀——MILVUS_URI 是 pymilvus 自己 import 时就读的环境变量。
os.environ["KB_MILVUS_URI"] = ""
os.environ["MONETIZATION_ENABLED"] = "false"
os.environ["APP_ENV"] = "development"
os.environ["PUBLIC_BASE_URL"] = ""
# 测试专用密钥，避免用 .env 里的真实 jwt_secret（长度需 ≥32 字节，否则 pyjwt 告警）
os.environ["JWT_SECRET"] = "test-only-secret-0123456789abcdef0123456789abcdef"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def seeded_user(client):
    """在临时库里造出 token 夹具对应的用户。

    get_current_user 现在会回查数据库（注销要能立刻生效），所以只伪造 token
    是不够的——库里没有这个 user_id 会直接 401。
    """
    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect(_TMP_DB)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users "
            "(id, openid, nickname, avatar, phone, city, is_vip, points, is_active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (999999, "mock_openid_test", "测试用户", "", "", "杭州", 0, 20, 1,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    finally:
        conn.close()
    return 999999


@pytest.fixture
def token(seeded_user):
    """已登录态的 Bearer token（用户 999999，由 seeded_user 建好）。"""
    from app.utils.jwt_utils import create_token

    return create_token({"user_id": 999999, "openid": "mock_openid_test"})


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tmp_index(monkeypatch, tmp_path):
    """检索层测试用的 Milvus 库：每个用例一个独立的 milvus-lite 数据文件。

    必须每个用例单独一个库（而不是共用一个集合）——否则上一个用例建好的索引
    会让下一个用例的「没有索引时返回 None」这类断言直接失效。
    """
    from app.config import settings
    from kb import retriever

    monkeypatch.setattr(settings, "kb_milvus_uri", (tmp_path / "kb.db").as_posix())
    monkeypatch.setattr(settings, "kb_milvus_collection", "kb_test")
    retriever.reset_caches()
    yield tmp_path
    retriever.reset_caches()

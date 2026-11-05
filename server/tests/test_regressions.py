"""本次代码审查修复的回归用例。

这些 bug 的共同点是「跑得通但结果是错的」——静态检查、启动、健康检查全绿，
只有真的断言行为才拦得住。每条用例对应审查报告里的一个编号。
"""
import asyncio
import sqlite3
import time
from datetime import datetime

import pytest
from pydantic import ValidationError

from tests.conftest import _TMP_DB


def _sql(stmt, params=()):
    conn = sqlite3.connect(_TMP_DB)
    try:
        cur = conn.execute(stmt, params)
        conn.commit()
        return cur
    finally:
        conn.close()


# —— P0-2 注销后旧 token 必须立刻失效 ——
def test_注销账号后旧token立即失效(client):
    from app.utils.jwt_utils import create_token

    _sql("DELETE FROM users WHERE id = ?", (999998,))
    _sql(
        "INSERT INTO users (id, openid, nickname, avatar, phone, city, is_vip, points, "
        "is_active, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (999998, "openid_cancel_test", "待注销", "", "", "杭州", 0, 20, 1,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    headers = {"Authorization": f"Bearer {create_token({'user_id': 999998, 'openid': 'openid_cancel_test'})}"}

    assert client.get("/api/user/me", headers=headers).status_code == 200

    _sql("UPDATE users SET is_active = 0 WHERE id = ?", (999998,))
    assert client.get("/api/user/me", headers=headers).status_code == 401
    # 注销后不能再用旧 token 写数据
    assert client.get("/api/trip/list", headers=headers).status_code == 401


# —— P0-3 验证码连续试错达到上限后作废 ——
def test_验证码试错超限后作废():
    from app.services import sms_service

    phone = "13800000001"
    code = "123456"
    sms_service._MEM.clear()
    sms_service._MEM[f"sms:code:{phone}"] = (code, time.time() + 300)

    for i in range(sms_service.MAX_VERIFY_ATTEMPTS):
        assert asyncio.run(sms_service.verify(phone, "000000")) is False

    # 超过上限后，即使拿对了验证码也不再放行
    assert asyncio.run(sms_service.verify(phone, code)) is False


# —— P0-4 生产环境漏配短信 key 必须失败，而不是把验证码回传前端 ——
def test_生产环境未配短信key时拒绝发送(monkeypatch):
    from app.config import settings
    from app.utils import sms as sms_util

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "sms_provider", "chuangxin")
    monkeypatch.setattr(settings, "chuangxin_app_code", "")

    with pytest.raises(RuntimeError):
        asyncio.run(sms_util.send_sms("13800000002", "654321"))


def test_开发环境未配短信key时回传验证码(monkeypatch):
    from app.config import settings
    from app.utils import sms as sms_util

    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "sms_provider", "chuangxin")
    monkeypatch.setattr(settings, "chuangxin_app_code", "")

    ok, dev_code = asyncio.run(sms_util.send_sms("13800000003", "654321"))
    assert ok is True and dev_code == "654321"


# —— P1-1 行程时间戳必须是毫秒；P1-2 status=all 不能当字面值过滤 ——
def test_行程列表时间戳是毫秒且status_all不过滤(client, auth):
    _sql("DELETE FROM trips WHERE id IN (900001, 900002)")
    for tid, status in ((900001, "active"), (900002, "archived")):
        _sql(
            "INSERT INTO trips (id, user_id, title, city, days, route_type, crowd_type, "
            "budget_level, total_budget, content, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, 999999, f"行程{tid}", "杭州", 2, "popular", "朋友", "舒适", 100,
             "{}", status, "2026-10-01 10:00:00"),
        )

    r = client.get("/api/trip/list", params={"status": "all"}, headers=auth).json()
    ids = [t["id"] for t in r["data"]["list"]]
    assert 900001 in ids and 900002 in ids, "status=all 应当返回全部行程"

    row = next(t for t in r["data"]["list"] if t["id"] == 900001)
    assert row["created_at"] > 1_000_000_000_000, "created_at 必须是毫秒时间戳"


# —— P1-3 收藏列表必须返回完整模板字段，且 id 是模板 id ——
def test_收藏列表返回完整模板(client, auth):
    _sql("DELETE FROM collections WHERE user_id = 999999")
    _sql("DELETE FROM templates WHERE id = 900010")
    _sql(
        "INSERT INTO templates (id, title, city, days, spots_count, route_type, cover, "
        "content, is_premium, uses, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (900010, "收藏测试模板", "杭州", 2, 6, "popular", "🏞️", "{}", 0, 10,
         "2026-10-01 10:00:00"),
    )
    _sql("INSERT INTO collections (user_id, template_id, created_at) VALUES (?,?,?)",
         (999999, 900010, "2026-10-01 10:00:00"))

    r = client.get("/api/collection/list", headers=auth).json()
    item = next(x for x in r["data"]["list"] if x["id"] == 900010)
    assert item["title"] == "收藏测试模板"
    assert item["city"] == "杭州" and item["cover"] == "🏞️"
    assert item["collection_id"], "需要额外返回收藏记录 id"


# —— P2-1 缺参返回 422，而不是 500 ——
@pytest.mark.parametrize("url", ["/api/collection/add", "/api/template/use",
                                 "/api/template/publish", "/api/trip/delete"])
def test_缺参返回422而不是500(client, auth, url):
    r = client.post(url, json={}, headers=auth)
    assert r.status_code == 422


# —— P2-2 同一秒内两次下单不能撞单号 ——
def test_订单号同秒不重复():
    from app.services.payment_service import payment_service

    first = asyncio.run(payment_service.create_order(999999, "month"))
    second = asyncio.run(payment_service.create_order(999999, "month"))
    assert first["order_no"] != second["order_no"]


# —— P2-4 积分扣减到 0 后不能再扣 ——
def test_积分不会扣成负数(client, auth):
    from app.services.points_service import points_service

    _sql("UPDATE users SET points = 5 WHERE id = 999999")
    assert asyncio.run(points_service.consume(999999, 5)) is True
    assert asyncio.run(points_service.consume(999999, 1)) is False
    assert asyncio.run(points_service.get_points(999999)) == 0
    _sql("UPDATE users SET points = 20 WHERE id = 999999")


# —— P1-8 行李清单必须按天数/季节/目的地分支 ——
def test_行李清单随季节和天数变化():
    from app.services.chat_service import chat_service

    summer = asyncio.run(chat_service.luggage("三亚", 5, "夏"))
    winter = asyncio.run(chat_service.luggage("哈尔滨", 2, "冬"))
    summer_items = sum((g["items"] for g in summer["list"]), [])
    winter_items = sum((g["items"] for g in winter["list"]), [])
    assert any("防晒" in x for x in summer_items)
    assert any("羽绒服" in x for x in winter_items)
    assert summer_items != winter_items

    hk = asyncio.run(chat_service.luggage("香港", 3, "秋"))
    hk_items = sum((g["items"] for g in hk["list"]), [])
    assert any("港澳通行证" in x for x in hk_items)


# —— P2-6 OCR 超大文件必须拒绝 ——
def test_OCR超大文件被拒绝(client, auth, monkeypatch):
    from app.routers import ocr

    monkeypatch.setattr(ocr, "MAX_B64_CHARS", 100)
    r = client.post("/api/ocr/recognize",
                    json={"file_base64": "A" * 200, "filename": "a.jpg"},
                    headers=auth).json()
    assert r["code"] == 413


# —— P2-9 生产环境禁止使用默认 JWT 密钥 / 必须配 Redis ——
def test_生产环境默认jwt密钥拒绝启动():
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(app_env="production", redis_url="redis://127.0.0.1:6379/0",
                 jwt_secret="dev-secret-change-me-please-replace-32bytes-min")

    # 正常配置可以启动
    cfg = Settings(app_env="production", redis_url="redis://127.0.0.1:6379/0",
                   jwt_secret="x" * 48)
    assert cfg.app_env == "production"


def test_生产环境缺少redis拒绝启动():
    """Redis 不是可选项：限流/验证码/短信频率/access_token 缓存全靠它，
    缺了会静默降级成进程内计数，多 worker 下额度翻倍。"""
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(app_env="production", redis_url="", jwt_secret="x" * 48)
    # 开发态不强制
    Settings(app_env="development", redis_url="", jwt_secret="dev-secret")


# —— 微信 access_token 必须走 Redis 共享（多 worker 不能各刷新各的） ——
def test_access_token多worker共享redis缓存(monkeypatch):
    import app.redis_client as rc
    import app.utils.wechat as wx

    class FakeRedis:
        def __init__(self):
            self.store = {}

        async def get(self, k):
            return self.store.get(k)

        async def set(self, k, v, ex=None):
            self.store[k] = v

        async def ttl(self, k):
            return 6000 if k in self.store else -2

    fake = FakeRedis()
    monkeypatch.setattr(rc, "redis_client", fake)
    monkeypatch.setattr(wx, "redis_client", fake)
    monkeypatch.setattr(wx.settings, "wx_app_id", "wx_test_appid")
    monkeypatch.setattr(wx.settings, "wx_app_secret", "sec")

    calls = {"n": 0}

    class FakeResp:
        def json(self):
            return {"access_token": "tok_abc", "expires_in": 7200}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None):
            calls["n"] += 1
            return FakeResp()

    monkeypatch.setattr(wx.httpx, "AsyncClient", lambda *a, **k: FakeClient())

    t1 = asyncio.run(wx.get_access_token())
    assert t1 == "tok_abc" and calls["n"] == 1

    # 清掉进程内缓存，只留 Redis —— 模拟同一台机上的第二个 worker 进程
    wx._TOKEN_CACHE["token"] = None
    wx._TOKEN_CACHE["exp"] = 0.0
    t2 = asyncio.run(wx.get_access_token())

    assert t2 == "tok_abc", "第二个 worker 应命中 Redis 缓存"
    assert calls["n"] == 1, f"第二个 worker 又打了一次接口（实际 {calls['n']} 次），缓存没共享"


# —— P2-5 微调同样要计费（变现开启时）——
def test_变现开启时微调扣积分(client, auth, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "monetization_enabled", True)
    _sql("UPDATE users SET points = 0 WHERE id = 999999")

    r = client.post("/api/plan/chat-adjust",
                    json={"trip": {}, "instruction": "改一下"}, headers=auth).json()
    assert r["code"] == 4001
    _sql("UPDATE users SET points = 20 WHERE id = 999999")

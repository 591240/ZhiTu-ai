"""CORS 中间件参数：开发态放行局域网，生产态必须只认白名单。

这个项目没有网页端（wx.request 不走同源策略），所以这里测的是配置函数的正确性，
而不是浏览器行为——将来真加管理后台时这套分支已经是绿的。
"""
from app.main import DEV_ORIGIN_REGEX, build_cors_kwargs


class _Cfg:
    def __init__(self, app_env, origins=""):
        self.app_env = app_env
        self._origins = [o.strip() for o in origins.split(",") if o.strip()]

    def cors_origin_list(self):
        return list(self._origins)


def test_开发态带局域网正则():
    kwargs = build_cors_kwargs(_Cfg("development"))
    assert kwargs["allow_origin_regex"] == DEV_ORIGIN_REGEX
    assert kwargs["allow_origins"] == []


def test_生产态绝不能带局域网正则():
    kwargs = build_cors_kwargs(_Cfg("production", "https://api.example.com"))
    assert "allow_origin_regex" not in kwargs, "生产环境仍放行局域网，等于没收紧"


def test_生产态白名单为逗号分隔且容忍空格空项():
    kwargs = build_cors_kwargs(_Cfg("production", "https://a.com, https://b.com ,"))
    assert kwargs["allow_origins"] == ["https://a.com", "https://b.com"]


def test_白名单里的裸通配会被剔掉():
    # allow_credentials=True 配 "*" 浏览器会直接拒绝，属于误配，不该原样透传
    kwargs = build_cors_kwargs(_Cfg("production", "*"))
    assert kwargs["allow_origins"] == []
    assert kwargs["allow_credentials"] is True


def test_运行时局域网来源被放行():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).options(
        "/api/user/feedback",
        headers={"Origin": "http://192.168.10.8:8081", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://192.168.10.8:8081"


def test_运行时外网来源被拒():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).options(
        "/api/user/feedback",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") is None

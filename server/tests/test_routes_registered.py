"""路由注册回归：专门锁住「函数写了但装饰器漏了」这类静默失效。

feedback 路由就是因为漏了 @router.post 装饰器，前端调用一直 404，
而服务启动、健康检查、其他接口全都正常——只有 openapi 路径表能直接暴露它。
"""
import pytest

from app.main import app


@pytest.fixture(scope="module")
def paths():
    return set(app.openapi()["paths"])


# 这些路径全部靠装饰器注册，漏一个就该在这里红
CRITICAL_PATHS = [
    "/api/user/feedback",
    "/api/user/profile",
    "/api/user/avatar",
    "/api/user/points",
    "/api/user/recharge",
    "/api/template/publish",
    "/api/template/hot",
    "/api/trip/save",
    "/api/plan/form",
    "/api/chat/qa",
    "/api/auth/login",
]


@pytest.mark.parametrize("path", CRITICAL_PATHS)
def test_关键路由必须已注册(paths, path):
    assert path in paths, f"{path} 未出现在路由表里——检查是不是漏了 @router 装饰器"


def test_路由总数没有莫名减少(paths):
    # 16 个路由模块聚合出来的接口，历史上加过 sms/track/ticket/map/ota/distribution
    assert len(paths) >= 40, f"路由数量只有 {len(paths)} 条，疑似有模块没挂上"


@pytest.mark.parametrize("url", ["/api/trip/list", "/api/template/hot", "/api/user/points"])
def test_未登录被鉴权拦截而不是报500(client, url):
    assert client.get(url).status_code == 401


def test_不存在的路径仍然404(client):
    assert client.get("/api/user/__nope__").status_code == 404

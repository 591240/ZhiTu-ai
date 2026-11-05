"""头像永久链接的推导。

部署用的 .env 里没有 PUBLIC_BASE_URL，之前的代码注释写着「默认用请求 host」但没实现，
结果线上会返回相对路径 /static/avatars/xxx，小程序 <image> 加载不出来。
"""
import glob

import pytest

from app.config import BASE_DIR

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture(autouse=True)
def _清理测试头像():
    yield
    for p in glob.glob(str(BASE_DIR / "static" / "avatars" / "u999999_*")):
        import os

        os.remove(p)


def test_配了公网域名时用配置值(client, auth):
    from app.config import settings

    original = settings.public_base_url
    settings.public_base_url = "https://api.fixed.com"
    try:
        r = client.post(
            "/api/user/avatar",
            headers=auth,
            files={"file": ("a.png", _PNG, "image/png")},
        )
        assert r.json()["data"]["avatar"].startswith("https://api.fixed.com/static/avatars/")
    finally:
        settings.public_base_url = original


def test_没配置时从网关转发头推导(client, auth):
    r = client.post(
        "/api/user/avatar",
        headers={**auth, "X-Forwarded-Host": "api.zhitu.com", "X-Forwarded-Proto": "https"},
        files={"file": ("a.png", _PNG, "image/png")},
    )
    url = r.json()["data"]["avatar"]
    assert url.startswith("https://api.zhitu.com/static/avatars/"), "外层 TLS 被网关透传后必须还是 https"


def test_没有转发头时退化成请求host(client, auth):
    url = client.post(
        "/api/user/avatar", headers=auth, files={"file": ("a.png", _PNG, "image/png")}
    ).json()["data"]["avatar"]
    assert url.startswith("http://testserver/static/avatars/")
    assert not url.startswith("/"), "相对路径在小程序里加载不了"


def test_非图片类型被拒(client, auth):
    r = client.post(
        "/api/user/avatar", headers=auth, files={"file": ("a.txt", b"hello", "text/plain")}
    )
    assert r.json()["code"] != 0

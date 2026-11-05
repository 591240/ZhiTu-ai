"""内容安全校验的分支覆盖。

约定：接口抖动一律放行（fail-open），只有明确 risky 才拦。
全部用假 httpx，不会真打微信接口——既省每日 token 配额，也保证离线能跑。
没有引入 pytest-asyncio，所以这里统一用 asyncio.run 包一层同步调用。
"""
import asyncio
from types import SimpleNamespace

import pytest

import app.utils.wechat as wx
from app.utils.wechat import check_text_security, collect_text


class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _Client:
    def __init__(self, data=None, exc=None):
        self.data, self.exc = data, exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *a, **k):
        if self.exc:
            raise self.exc
        return _Resp(self.data)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def no_network(monkeypatch):
    """任何一次网络/token 调用都算测试失败。"""

    def _boom(*a, **k):
        raise AssertionError("不该发起 HTTP 请求")

    async def _no_token():
        raise AssertionError("不该去取 access_token")

    monkeypatch.setattr(wx.httpx, "AsyncClient", _boom)
    monkeypatch.setattr(wx, "get_access_token", _no_token)


@pytest.fixture
def configured(monkeypatch):
    async def _token():
        return "fake-token"

    monkeypatch.setattr(wx, "settings", SimpleNamespace(wx_app_id="wx_test", wx_app_secret="sec"))
    monkeypatch.setattr(wx, "get_access_token", _token)
    return monkeypatch


def _reply(monkeypatch, data=None, exc=None):
    monkeypatch.setattr(wx.httpx, "AsyncClient", lambda **kw: _Client(data, exc))


def test_没配微信密钥时直接放行(no_network, monkeypatch):
    monkeypatch.setattr(wx, "settings", SimpleNamespace(wx_app_id="", wx_app_secret=""))
    assert _run(check_text_security("随便写点什么", openid="real_openid")) == (True, "")


def test_mock登录态不发请求(no_network, monkeypatch):
    """无 AppID 时登录发的是 mock_openid，微信只会回 40003，白烧一次调用。"""
    monkeypatch.setattr(wx, "settings", SimpleNamespace(wx_app_id="wx_test", wx_app_secret="sec"))
    assert _run(check_text_security("内容", openid="mock_openid_abc123")) == (True, "")


def test_空内容不发请求(no_network, monkeypatch):
    monkeypatch.setattr(wx, "settings", SimpleNamespace(wx_app_id="wx_test", wx_app_secret="sec"))
    assert _run(check_text_security("   ", openid="real_openid")) == (True, "")


def test_命中违规才拦截(configured):
    _reply(configured, {"errcode": 0, "result": {"suggest": "risky", "label": 20001}})
    passed, msg = _run(check_text_security("违规内容", openid="real_openid"))
    assert passed is False
    assert msg, "拦截必须带回给用户看的文案"


def test_需要复审仍放行(configured):
    _reply(configured, {"errcode": 0, "result": {"suggest": "review"}})
    assert _run(check_text_security("擦边内容", openid="real_openid")) == (True, "")


def test_无法判定87030放行(configured):
    _reply(configured, {"errcode": 87030, "errmsg": "user has no recent visit"})
    assert _run(check_text_security("内容", openid="real_openid")) == (True, "")


def test_接口异常放行(configured):
    _reply(configured, exc=RuntimeError("timeout"))
    assert _run(check_text_security("内容", openid="real_openid")) == (True, "")


def test_凭据失效等其他错误码也放行(configured):
    _reply(configured, {"errcode": 40001, "errmsg": "invalid credential"})
    assert _run(check_text_security("内容", openid="real_openid")) == (True, "")


def test_超长内容被截到2500字(configured):
    captured = {}

    class _Capture(_Client):
        async def post(self, url, params=None, json=None):
            captured["content"] = json["content"]
            return _Resp({"errcode": 0, "result": {"suggest": "pass"}})

    configured.setattr(wx.httpx, "AsyncClient", lambda **kw: _Capture())
    _run(check_text_security("字" * 9000, openid="real_openid"))
    assert len(captured["content"]) == 2500, "超出微信 content 上限会被直接拒"


def test_collect_text能拍平行程结构():
    obj = {"itinerary": [{"spots": [{"name": "西湖", "ticket_price": 0}]}], "weather_tip": "多云"}
    text = collect_text(obj)
    assert "西湖" in text and "多云" in text
    assert len(collect_text({"a": "x" * 5000})) <= 2500

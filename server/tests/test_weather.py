"""真实天气服务。核心断言只有一句：模型写的天气必须被真实预报覆盖。

全部离线：用假 requests，不真打高德（那把 key 有 QPS 限制）。
"""
import copy
from datetime import date

import pytest

from app.config import settings
from app.services import weather_service as W
from app.services.plan_service import SCHEMA_HINT, gen_trip

CITY = "杭州"
TODAY = date.today().isoformat()


def _mk(day1: str, weather: str = "多云", hi: str = "20", lo: str = "12"):
    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "1", "info": "OK", "forecasts": [{"city": CITY, "casts": [
                {"date": day1, "dayweather": weather, "nightweather": "晴", "daytemp": hi,
                 "nighttemp": lo, "daywind": "东北", "daypower": "1-3"},
                {"date": day1, "nightweather": "晴", "dayweather": weather, "daytemp": hi,
                 "nighttemp": lo, "daywind": "东北", "daypower": "1-3"},
                {"date": "2099-01-01", "dayweather": "小雨", "nightweather": "小雨", "daytemp": "9",
                 "nighttemp": "5", "daywind": "北", "daypower": "5-6"},
            ]}]}

    return _R()


@pytest.fixture(autouse=True)
def _隔离(monkeypatch):
    W._cache.clear()
    snap = dict(W.STATS)
    monkeypatch.setattr(settings, "gaode_web_key", "fake-key", raising=False)
    yield
    W._cache.clear()
    W.STATS.clear()
    W.STATS.update(snap)


def _fake_get(payload):
    def _get(url, params=None, timeout=None):
        return payload
    return _get


def test_按日期索引解析预报(monkeypatch):
    monkeypatch.setattr(W.requests, "get", _fake_get(_mk(TODAY)))
    fc = W.get_forecast(CITY)
    assert TODAY in fc
    assert fc[TODAY]["day_weather"] == "多云"
    assert fc[TODAY]["day_temp"] == "20" and fc[TODAY]["night_temp"] == "12"


def test_同一城市只请求一次(monkeypatch):
    calls = []

    def _get(url, params=None, timeout=None):
        calls.append(params["city"])
        return _mk(TODAY)

    monkeypatch.setattr(W.requests, "get", _get)
    W.get_forecast(CITY)
    W.get_forecast(CITY)
    assert calls == [CITY], "重复规划不该再打高德（key 有 QPS 限制）"


def test_没配key或空城市不发请求(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("不该发请求")

    monkeypatch.setattr(W.requests, "get", _boom)
    monkeypatch.setattr(settings, "gaode_web_key", "", raising=False)
    assert W.get_forecast(CITY) == {}
    monkeypatch.setattr(settings, "gaode_web_key", "fake-key", raising=False)
    assert W.get_forecast("") == {}


def test_接口异常与失败状态都返回空(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("timeout")

    monkeypatch.setattr(W.requests, "get", _boom)
    assert W.get_forecast(CITY) == {}
    assert W.STATS["failed"] == 1

    class _Bad:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "0", "info": "CUQPS_HAS_EXCEEDED_THE_LIMIT"}

    monkeypatch.setattr(W.requests, "get", _fake_get(_Bad()))
    assert W.get_forecast("武汉") == {}


def test_日期展开与边界():
    assert W.resolve_dates("2026-11-07", 2)[0] == date(2026, 11, 7)
    assert len(W.resolve_dates("2026-11-07", 3)) == 3
    assert W.resolve_dates("", 2)[0] == date.today(), "缺出发日期时从今天算"
    assert W.resolve_dates("乱写的", 2)[0] == date.today()
    assert len(W.resolve_dates("2026-11-07", 0)) == 1
    assert len(W.resolve_dates("2026-11-07", 99)) <= 7


def test_雨天给出排程建议(monkeypatch):
    monkeypatch.setattr(W, "get_forecast", lambda city: {TODAY: {
        "day_weather": "中雨", "night_weather": "小雨", "day_temp": "18", "night_temp": "14", "wind": "东北风1-3级"}})
    text, advice = W.day_tip(CITY, date.today())
    assert "中雨" in text and "14~18℃" in text
    assert "室内" in advice


def test_高温与大风建议(monkeypatch):
    def fake(w, hi, wind):
        monkeypatch.setattr(W, "get_forecast", lambda city: {TODAY: {
            "day_weather": w, "night_weather": w, "day_temp": hi, "night_temp": "20", "wind": wind}})
        return W.day_tip(CITY, date.today())[1]

    assert "高温" in fake("晴", "37", "西南风1-3级")
    assert "低温" in fake("晴", "3", "东北风1-3级")
    assert "风力" in fake("晴", "20", "北风6-7级")


def test_超出预报范围要如实说明(monkeypatch):
    monkeypatch.setattr(W, "get_forecast", lambda city: {TODAY: {
        "day_weather": "晴", "night_weather": "晴", "day_temp": "20", "night_temp": "10", "wind": "微风1-3级"}})
    text, _ = W.day_tip(CITY, date(2099, 1, 1))
    assert "超出可预报范围" in text and "实时" in text
    assert W.STATS["days_out_of_range"] == 1

    text2, _ = W.day_tip(CITY, date(2020, 1, 1))
    assert "暂未获取到" in text2


def test_没有真实天气时不往prompt塞假数据(monkeypatch):
    monkeypatch.setattr(W, "get_forecast", lambda city: {})
    assert W.trip_weather_block(CITY, TODAY, 2) == ""


def test_prompt块含逐日真实天气(monkeypatch):
    monkeypatch.setattr(W, "get_forecast", lambda city: {TODAY: {
        "day_weather": "多云", "night_weather": "晴", "day_temp": "20", "night_temp": "12", "wind": "东北风1-3级"}})
    block = W.trip_weather_block(CITY, TODAY, 2)
    assert "真实天气" in block and "禁止自行编造" in block and "第1天" in block


def test_模型瞎写的天气被强制覆盖(monkeypatch):
    """这是 B2 的全部意义：weather_tip 是事实字段，不能由模型决定。"""
    monkeypatch.setattr(W, "get_forecast", lambda city: {TODAY: {
        "day_weather": "小雨", "night_weather": "中雨", "day_temp": "17", "night_temp": "13", "wind": "北风1-3级"}})
    content = {"itinerary": [{"weather_tip": "今日晴，注意防晒补水"}, {"weather_tip": "大晴天，适合拍照"}]}
    n = W.apply_to_trip(content, CITY, TODAY, 2)
    assert n == 2
    assert "小雨" in content["itinerary"][0]["weather_tip"]
    assert "晴" not in content["itinerary"][0]["weather_tip"]
    assert "今日晴" not in content["itinerary"][1]["weather_tip"]


def test_旧版写死的今日晴示例已从prompt删除():
    assert "今日晴" not in SCHEMA_HINT, "prompt 里的示例会被模型照抄成编造天气"


def test_离线生成器不引入网络调用(monkeypatch):
    """gen_trip 被模板 seed 和 OCR 链路复用，必须保持纯离线，否则启动就要打高德。"""
    def _boom(*a, **k):
        raise AssertionError("gen_trip 不该发网络请求")

    monkeypatch.setattr(W.requests, "get", _boom)
    trip = gen_trip({"city": "杭州", "days": 2})
    assert trip["content"]["itinerary"][0]["weather_tip"]

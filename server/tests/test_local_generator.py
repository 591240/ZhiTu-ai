"""本地行程生成器的结构不变量。

它是 OCR 识图（ocr_service）和模板广场 seed（template_service）的共同上游，
也是 RAG 改造前唯一的安全网——重构时这些断言必须一直是绿的。
"""
import json

import pytest

from app.services.plan_service import SPOTS, gen_trip


def _params(city, days=2, route_type="popular", **extra):
    p = {"city": city, "days": days, "route_type": route_type}
    p.update(extra)
    return p


@pytest.mark.parametrize("city", sorted(SPOTS))
@pytest.mark.parametrize("route_type", ["popular", "niche"])
def test_已有景点库城市能生成完整行程(city, route_type):
    trip = gen_trip(_params(city, days=2, route_type=route_type))
    days = trip["content"]["itinerary"]
    assert len(days) == 2
    for d in days:
        assert d["spots"], f"{city}/{route_type} 第 {d['day_number']} 天没有景点"
        for s in d["spots"]:
            assert s.get("name"), "存在无名称景点，前端时间轴会渲染成空白"


@pytest.mark.parametrize("city", ["某个没库的城市", ""])
def test_无景点库城市走通用模板也不能留占位符(city):
    trip = gen_trip(_params(city, days=3))
    blob = json.dumps(trip, ensure_ascii=False)
    assert "{city}" not in blob, "通用模板没被替换，用户会看到 {city}老街"


def test_天数被夹在1到4之间():
    assert len(gen_trip(_params("杭州", days=9))["content"]["itinerary"]) == 4
    assert len(gen_trip(_params("杭州", days=0))["content"]["itinerary"]) == 1
    assert len(gen_trip(_params("杭州", days=-3))["content"]["itinerary"]) == 1


def test_预算上下限颠倒时自动修正():
    trip = gen_trip(_params("杭州", budget_min=1500, budget_max=500))
    assert trip["budget_max"] >= trip["budget_min"]


def test_总预算是非负整数():
    total = gen_trip(_params("成都", days=3))["content"]["total_budget"]
    assert isinstance(total, int) and total >= 0


def test_返回结构与前端契约一致():
    trip = gen_trip(_params("西安"))
    assert set(trip["content"]) >= {"itinerary", "total_budget", "transport_plans", "budget_analysis", "preparations"}
    day = trip["content"]["itinerary"][0]
    assert set(day) >= {"day_number", "spots", "meals", "transport", "budget", "tips"}

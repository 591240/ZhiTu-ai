"""候选池与景点真实性校验。

这条链路的原则：拿不到真实名单就当没这回事（fail-open），
绝不允许因为高德配额/网络问题把整次行程生成搞挂——你们已经因为
「高德配额超限」出过一次"AI 生成一直转圈"的事故。
"""
import asyncio

import pytest

from app.services.plan_service import PlanService
from kb import candidates as C

_REAL_AMAP = C._amap_spots  # 抓住真实函数，绕开下面 fixture 装的默认桩


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _隔离缓存与统计(monkeypatch):
    """默认桩掉高德：语料城市条目少于池上限时会触发补查，
    不清掉就会出现「每条测试都真打一次外网 + 撞 QPS 限流」。
    要测真实解析的用例自己覆盖 requests.get 并直接调 _amap_spots。
    """
    C._pool_cache.clear()
    snapshot = dict(C.STATS)
    monkeypatch.setattr(C, "_amap_spots", lambda city: [])
    monkeypatch.setattr(C, "is_real_attraction", lambda name, city: False)
    yield
    C._pool_cache.clear()
    C.STATS.clear()
    C.STATS.update(snapshot)


POOL = [
    {"name": "西湖", "address": "西湖区", "category": "自然风光", "ticket_price": 0,
     "duration_min": 180, "need_booking": False, "photo_spots": [], "source": "corpus"},
    {"name": "灵隐寺", "address": "法云弄1号", "category": "人文历史", "ticket_price": 75,
     "duration_min": 150, "need_booking": True, "photo_spots": [], "source": "corpus"},
    {"name": "河坊街", "address": "上城区", "category": "美食", "ticket_price": 0,
     "duration_min": 120, "need_booking": False, "photo_spots": [], "source": "corpus"},
]


def _content(spot_names):
    return {"itinerary": [{"spots": [{"name": n} for n in spot_names]}]}


def test_find支持简称与后缀():
    assert C.find(POOL, "西湖")["name"] == "西湖"
    assert C.find(POOL, "杭州西湖风景区")["name"] == "西湖"
    assert C.find(POOL, "灵隐寺景区")["name"] == "灵隐寺"
    assert C.find(POOL, "雷峰塔") is None


def test_校验把编造景点换成池内同类项():
    res = C.verify_itinerary(_content(["西湖", "杭州梦幻乐园"]), "杭州")
    # 语料池里杭州有这些景点，编的那条必然被换掉或保留，但绝不会保持原名
    assert res["checked"] == 2
    assert res["aligned"] >= 1
    assert res["pool_size"] >= 2


def test_用户点名的必去点不被替换():
    content = _content(["上海迪士尼"])
    res = C.verify_itinerary(content, "杭州", must_see="上海迪士尼")
    assert res["unverified"] == 1
    assert content["itinerary"][0]["spots"][0]["name"] == "上海迪士尼"


def test_替换不产生同一天重复景点(monkeypatch):
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    content = _content(["假景点A", "假景点B"])
    res = C.verify_itinerary(content, "杭州")
    names = [s["name"] for s in content["itinerary"][0]["spots"]]
    assert len(names) == 2
    assert len(set(names)) == 2, f"替换后出现重复景点: {names}"
    assert res["replaced"] == 2


def test_同类目优先替换(monkeypatch):
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    content = {"itinerary": [{"spots": [{"name": "假人文景点", "category": "人文历史"}]}]}
    C.verify_itinerary(content, "杭州")
    assert content["itinerary"][0]["spots"][0]["name"] == "灵隐寺"


def test_真实字段覆盖模型估值(monkeypatch):
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    content = {"itinerary": [{"spots": [{"name": "灵隐寺", "ticket_price": 0, "need_booking": False}]}]}
    C.verify_itinerary(content, "杭州")
    spot = content["itinerary"][0]["spots"][0]
    assert spot["ticket_price"] == 75, "语料里的真实票价必须覆盖模型瞎猜"
    assert spot["need_booking"] is True


def test_池为空时完全不动行程(monkeypatch):
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: [])
    content = _content(["任意编的景点"])
    res = C.verify_itinerary(content, "拉萨")
    assert res["pool_size"] == 0 and res["checked"] == 0
    assert content["itinerary"][0]["spots"][0]["name"] == "任意编的景点"


def test_高德拿不到时退回语料池(monkeypatch):
    monkeypatch.setattr(C, "_amap_spots", lambda city: [])
    pool = C.city_pool("杭州")
    assert pool and all(p["source"] == "corpus" for p in pool)


def test_候选池结果被缓存不重复请求(monkeypatch):
    calls = []

    def _fake(city):
        calls.append(city)
        return [{"name": f"{city}A", "address": "", "category": "", "ticket_price": None,
                 "duration_min": None, "need_booking": False, "photo_spots": [], "source": "amap"}]

    monkeypatch.setattr(C, "_amap_spots", _fake)
    C.city_pool("武汉")
    C.city_pool("武汉")
    assert calls == ["武汉"], "同一城市第二次规划不该再打一次高德（key 有 QPS 限制）"


def test_高德返回解析真实结构(monkeypatch):
    """营业时间/评分在 biz_ext 下（biz 是 null）——字段路径搞错就会误判成"高德没这个数据"。"""
    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "1", "pois": [
                {"name": "故宫博物院", "address": "景山前街4号", "type": "风景名胜;风景名胜",
                 "location": "116.39,39.91", "keytag": "5A景区", "tel": "010-85007421",
                 "biz": None,
                 "biz_ext": {"rating": "4.9", "cost": [],
                             "opentime2": "周二至周日 08:30-17:00，周一全天关闭"}},
                {"name": "", "address": "脏数据"},
            ]}

    seen = {}

    def _get(url, params=None, timeout=None):
        seen.update(params or {})
        return _R()

    monkeypatch.setattr(C.settings, "gaode_web_key", "fake", raising=False)
    monkeypatch.setattr(C.requests, "get", _get)
    pool = _REAL_AMAP("北京")
    assert [p["name"] for p in pool] == ["故宫博物院"]
    assert seen["types"] == C.ATTRACTION_TYPES and seen["citylimit"] == "true"
    assert pool[0]["location"] == "116.39,39.91"
    assert "周一全天关闭" in pool[0]["open_time"], "营业时间必须从 biz_ext.opentime2 取"
    assert pool[0]["rating"] == "4.9" and pool[0]["keytag"] == "5A景区"
    assert pool[0]["tel"] == "010-85007421"


def test_高德异常只记失败不抛出(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("CUQPS_HAS_EXCEEDED_THE_LIMIT")

    monkeypatch.setattr(C.settings, "gaode_web_key", "fake", raising=False)
    monkeypatch.setattr(C.requests, "get", _boom)
    assert _REAL_AMAP("武汉") == []
    assert C.STATS["amap_failed"] == 1


def test_format_pool带门票与预约信息():
    text = C.format_pool(POOL)
    assert "灵隐寺" in text and "需预约" in text and "门票约75元" in text
    assert "西湖" in text and "免费" in text


def test_prompt里的名单约束与降级(monkeypatch):
    hint = PlanService._pool_hint("杭州")
    assert "候选景点" in hint and "不得新增" in hint

    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: [])
    assert PlanService._pool_hint("某小城") == "", "拿不到名单时不该往 prompt 里塞空名单"
    assert PlanService._pool_hint("") == ""


def test_池外但POI证实存在的景点保留(monkeypatch):
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    monkeypatch.setattr(C, "is_real_attraction", lambda name, city: True)
    content = _content(["西溪湿地"])
    res = C.verify_itinerary(content, "杭州")
    assert res["unverified"] == 1 and res["replaced"] == 0
    assert content["itinerary"][0]["spots"][0]["name"] == "西溪湿地"


def test_POI复核有调用预算(monkeypatch):
    """模型不听话写满池外名字时，不能让它把高德配额打爆（实测 6 次就 CUQPS）。"""
    calls = []
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    monkeypatch.setattr(C, "is_real_attraction", lambda name, city: calls.append(name) or False)
    content = _content(["假1", "假2", "假3", "假4", "假5", "假6"])
    res = C.verify_itinerary(content, "杭州", max_poi_checks=2)
    assert len(calls) == 2, "超出预算就不该继续查 POI"
    assert len(content["itinerary"][0]["spots"]) == 6, "spots 数量不能被校验改变"
    assert res["poi_checked"] == 0
    # 池里只有 3 条真实景点：前 3 条被换掉，后 3 条在池耗尽后原样保留——
    # 既不虚构也不删结构（实际池上限 18，每天最多 4-6 个景点，正常不会走到这里）
    assert res["replaced"] == 3 and res["unverified"] == 3


def test_指令点名的景点保留但仍复核真实性(monkeypatch):
    """用户点名 ≠ 景点存在：编造地名必须给出可展示的提示，而不是静默照单全收。"""
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    calls = []
    monkeypatch.setattr(C, "is_real_attraction", lambda name, city: calls.append(name) or False)
    content = _content(["海昌海洋公园"])
    res = C.verify_itinerary(content, "杭州", instruction="把第二天下午换成海昌海洋公园")
    assert content["itinerary"][0]["spots"][0]["name"] == "海昌海洋公园", "用户点名的一律保留"
    assert res["replaced"] == 0
    assert calls == ["海昌海洋公园"], "保留不等于不核查"
    assert res["notices"] and "未在高德景点库收录" in res["notices"][0]["notice"]


def test_点名的景点经查实存在则无提示(monkeypatch):
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    monkeypatch.setattr(C, "is_real_attraction", lambda name, city: True)
    content = _content(["海昌海洋公园"])
    res = C.verify_itinerary(content, "杭州", instruction="换成海昌海洋公园")
    assert res["notices"] == []
    assert res["unverified"] == 1


def test_POI复核不通过则替换(monkeypatch):
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    monkeypatch.setattr(C, "is_real_attraction", lambda name, city: False)
    content = _content(["不存在的游乐园"])
    res = C.verify_itinerary(content, "杭州")
    assert res["replaced"] == 1
    assert content["itinerary"][0]["spots"][0]["name"] != "不存在的游乐园"


def test_微调链路也会走景点校验并带上用户指令(monkeypatch):
    from app.config import settings
    from app.services.plan_service import plan_service

    seen = {}

    def _spy(content, city, must_see="", instruction="", **kw):
        seen["city"] = city
        seen["instruction"] = instruction
        return {"pool_size": 1, "checked": 0, "aligned": 0, "replaced": 0,
                "unverified": 0, "poi_checked": 0, "details": []}

    async def _fake_json(prompt):
        assert "候选景点" in prompt, "微调 prompt 也必须给模型真实名单"
        return {"reply": "已调整", "city": "杭州", "days": 2,
                "content": {"itinerary": [{"spots": [{"name": "幻觉景点"}]}]}}

    monkeypatch.setattr(settings, "llm_api_key", "fake", raising=False)
    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    monkeypatch.setattr(C, "verify_itinerary", _spy)
    monkeypatch.setattr("app.services.plan_service.llm_client.generate_json", _fake_json)

    reply, trip = _run(plan_service.adjust({"city": "杭州", "id": 7}, "把第二天换成海昌海洋公园"))
    assert seen["city"] == "杭州"
    assert "海昌海洋公园" in seen["instruction"], "微调必须把指令传进校验，否则会替换掉用户点名的景点"
    assert trip.get("id") == 7, "微调后必须保留行程 id，否则前端保存会变成新建"


def test_微调prompt带候选名单(monkeypatch):
    from app.services.plan_service import PlanService

    monkeypatch.setattr(C, "city_pool", lambda city, use_cache=True: list(POOL))
    prompt = PlanService()._adjust_prompt({"city": "杭州"}, "加个夜景")
    assert "候选景点" in prompt and "灵隐寺" in prompt and "不得引入" in prompt


def test_空城市名返回空池():
    assert C.city_pool("") == []
    assert C.verify_itinerary({"itinerary": []}, "")["checked"] == 0

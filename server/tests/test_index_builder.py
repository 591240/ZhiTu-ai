"""C1 索引扩容：语料 + 候选池一起进索引，以及必须跟着扩的城市识别。

最容易出错的地方不是 embedding，而是「城市集合」：
detect_city 和关键词退路原来都只认手写语料的 9 城，扩了 POI 城市如果不同步，
「北京故宫要预约吗」就锁不住北京，城市硬过滤等于失效——所以这几条断言是重点。
"""
import pytest

from kb import corpus, index_builder, retriever
from kb.retriever import Index, Retriever, detect_city, keyword_search
from kb.index_builder import build_docs, target_cities
from kb.corpus import merge_docs, poi_doc

POOL_ITEM = {"name": "故宫博物院", "address": "景山前街4号", "category": "风景名胜",
             "location": "116.39,39.91", "rating": "4.9", "open_time": "",
             "ticket_price": None, "duration_min": None, "need_booking": False,
             "photo_spots": [], "source": "amap"}


def test_poi_doc结构与语料一致():
    d = poi_doc(POOL_ITEM, "北京")
    assert d["id"] == "北京|spot|故宫博物院"
    assert d["kind"] == "spot" and d["city"] == "北京" and d["name"] == "故宫博物院"
    assert "景山前街4号" in d["text"] and "评分4.9" in d["text"]
    assert d["meta"]["location"] == "116.39,39.91"
    assert d["meta"]["source"] == "amap"


def test_poi_doc带上营业时间与电话才算有事实价值():
    """扩城市的意义就在于 POI 能给出真实开放时间；漏了就只能回答"资料未收录"。"""
    d = poi_doc({**POOL_ITEM, "keytag": "5A景区", "tel": "010-85007421",
                 "open_time": "周二至周日 08:30-17:00，周一全天关闭"}, "北京")
    assert "周一全天关闭" in d["text"]
    assert "010-85007421" in d["text"]
    assert "5A景区" in d["text"]
    assert d["meta"]["open_time"].startswith("周二至周日")


def test_poi_doc跳过空字段():
    d = poi_doc({"name": "某公园", "address": "", "category": "", "rating": "",
                 "location": "", "open_time": "", "ticket_price": None,
                 "duration_min": None, "need_booking": False, "photo_spots": []}, "天津")
    assert d["text"] == "天津·某公园"


def test_merge_docs按id去重且先到先得():
    a = poi_doc(POOL_ITEM, "北京")
    b = poi_doc({**POOL_ITEM, "address": "另一个地址"}, "北京")
    merged = merge_docs([a], [b])
    assert len(merged) == 1
    assert "景山前街4号" in merged[0]["text"], "语料/先到的文档必须优先，不能被 POI 覆盖"


def test_默认城市表是语料9城加12城():
    cities = target_cities()
    assert len(cities) == 21, f"期望 9 语料 + 12 扩城，实得 {len(cities)}"
    assert len(cities) == len(set(cities)), "语料里已有的城市不该被重复加入"
    assert {"北京", "珠海"} <= set(cities)


def test_指定城市时不叠加默认清单():
    assert target_cities(["北京", " 广州 ", ""]) == ["北京", "广州"]


@pytest.fixture
def fake_pool(monkeypatch):
    """假候选池，避免真打高德；也避免真 sleep。"""
    def _pool(city, use_cache=True):
        return [
            {"name": f"{city}地标", "address": f"{city}中心", "category": "风景名胜",
             "location": "0,0", "rating": "4.5", "open_time": "", "ticket_price": None,
             "duration_min": None, "need_booking": False, "photo_spots": [], "source": "amap"},
            # 故意放一个语料里已有的景点，验证不会被重复计入
            {"name": "西湖", "address": "西湖区", "category": "自然风光", "location": "",
             "rating": "", "open_time": "", "ticket_price": None, "duration_min": None,
             "need_booking": False, "photo_spots": [], "source": "amap"},
        ]

    monkeypatch.setattr(index_builder.candidates, "city_pool", _pool)
    return _pool


def test_扩池后新城市进入文档集(fake_pool):
    docs = build_docs(["杭州", "北京"], use_poi=True, interval=0)
    cities = {d["city"] for d in docs}
    assert {"杭州", "北京"} <= cities
    assert any(d["name"] == "北京地标" for d in docs)


def test_语料已有景点不被POI重复计入(fake_pool):
    docs = build_docs(["杭州"], use_poi=True, interval=0)
    hu = [d for d in docs if d["name"] == "西湖"]
    assert len(hu) == 1, "候选池里的西湖不该再生成一条 POI 文档"
    assert "路线" in hu[0]["text"], "保留的必须是语料那条（有玩法/机位），不能被信息更少的 POI 文档顶掉"


def test_关掉POI时只有语料城市(fake_pool):
    docs = build_docs(["北京", "珠海"], use_poi=False, interval=0)
    assert docs == [], "无语料且不开 POI 时不该凭空造文档"


def _doc(city, name):
    return {"id": f"{city}|spot|{name}", "kind": "spot", "city": city, "name": name,
            "text": f"{city}·{name}；需提前预约", "meta": {}}


def test_索引里的新城市能被城市识别认出来(tmp_index, monkeypatch):
    """这是 C1 的关键耦合：只扩索引不扩识别，城市硬过滤就还是 9 城。"""
    docs = [_doc("北京", "故宫博物院"), _doc("杭州", "西湖")]
    retriever.save_index(Index(docs, [[1.0, 0.0], [0.0, 1.0]]))
    monkeypatch.setattr(retriever.embedder, "embed_one", lambda q: [1.0, 0.0])
    retriever.reset_caches()

    assert detect_city("北京故宫博物院要预约吗") == "北京"
    hits = Retriever().search("故宫要预约吗", city="北京")["hits"]
    assert hits and hits[0]["city"] == "北京"


def test_关键词退路也覆盖POI城市(tmp_index, monkeypatch):
    docs = [_doc("珠海", "长隆海洋王国")]
    retriever.save_index(Index(docs, [[1.0, 0.0]]))
    monkeypatch.setattr(retriever.embedder, "embed_one", lambda q: None)  # 逼它走退路
    r = Retriever()
    out = r.search("长隆海洋王国", city="珠海")
    assert out["mode"] == "keyword"
    assert out["hits"] and out["hits"][0]["city"] == "珠海"


def test_reset_caches会重新派生城市表(monkeypatch):
    monkeypatch.setattr(retriever, "_CITY_NAMES", ["杭州"])
    retriever.reset_caches()
    assert retriever._CITY_NAMES is None, "不清缓存的话，扩城市后识别表还是旧的"
    assert detect_city("杭州西湖") == "杭州"
    assert retriever._CITY_NAMES is not None

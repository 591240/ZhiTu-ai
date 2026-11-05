"""检索层测试：embedding 全部用假向量，绝不真调百炼接口。

存储层不 mock——每个用例一个独立的 milvus-lite 临时库（conftest 的 tmp_index 夹具），
因为要验的正是「向量真的写进去、取回来还能算对分」这件事。

其中 test_城市过滤挡住跨城串味 复刻了实测事故：问「灵隐寺需要预约吗」时
语义第二近的是「北京故宫：需提前7天预约」。这种串味调阈值调不掉，只能靠 city 硬过滤。
"""
import math

import pytest

from kb import corpus, embedder, retriever
from kb.retriever import Index, Retriever, keyword_search, load_index, save_index


@pytest.fixture
def docs():
    return corpus.build_docs()


def test_语料覆盖全部9城(docs):
    assert {d["city"] for d in docs} == set(corpus.load_spots())


def test_每条文档都能独立回答(docs):
    for d in docs:
        assert d["id"] and d["city"] and d["name"] and d["text"]
        assert d["kind"] in {"spot", "meal"}
        assert len(d["text"]) > 8, f"{d['id']} 文本太短，检索不到有效事实"


def test_文档id不重复(docs):
    ids = [d["id"] for d in docs]
    assert len(ids) == len(set(ids)), "同一景点在大众/小众路线重复时必须合并成一条"


def test_景点文档带预约与票价事实(docs):
    spot = next(d for d in docs if d["kind"] == "spot")
    assert isinstance(spot["meta"]["need_booking"], bool)
    assert "门票" in spot["text"] or spot["meta"]["ticket_price"] in (0, None)


def test_truthy兼容语料里的混乱写法():
    for t in (True, "true", "TRUE", 1, "是", "需要"):
        assert corpus._truthy(t) is True, t
    for f in (False, "false", 0, "", None, "否", "无需"):
        assert corpus._truthy(f) is False, f


def test_归一化后是单位向量():
    v = embedder.normalize([3.0, 4.0])
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-9)


def test_批量返回按index排序(monkeypatch):
    """上游不保证 data 顺序与输入一致，这里必须自己按 index 排。"""
    class _R:
        status_code = 200

        def json(self):
            return {"data": [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}]}

    monkeypatch.setattr(embedder, "configured", lambda: True)
    monkeypatch.setattr(embedder, "endpoint", lambda: ("https://x/v1", "k"))
    monkeypatch.setattr(embedder, "_load_cache", lambda: {})
    monkeypatch.setattr(embedder, "_save_cache", lambda c: None)
    monkeypatch.setattr(embedder.requests, "post", lambda *a, **k: _R())
    assert embedder.embed(["第一条", "第二条"]) == [[1.0, 0.0], [0.0, 1.0]]


def test_接口失败返回None而不是抛异常(monkeypatch):
    monkeypatch.setattr(embedder, "configured", lambda: True)
    monkeypatch.setattr(embedder, "endpoint", lambda: ("https://x/v1", "k"))
    monkeypatch.setattr(embedder, "_load_cache", lambda: {})

    def _boom(*a, **k):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(embedder.requests, "post", _boom)
    assert embedder.embed(["内容"]) is None


def test_embedding缓存只解析一次(monkeypatch, tmp_path):
    """缓存文件已近 3MB，每次查询重新解析会给每个问题白加几十毫秒。"""
    target = tmp_path / "embed_cache.json"
    target.write_text('{"k": [1.0, 0.0]}', encoding="utf-8")
    monkeypatch.setattr(embedder, "CACHE_FILE", target)
    monkeypatch.setattr(embedder, "_CACHE_MEM", None)

    first = embedder._load_cache()
    assert first == {"k": [1.0, 0.0]}
    target.unlink()
    assert embedder._load_cache() is first, "已命中内存缓存就不该再读盘，更不该因文件缺失报错"


def test_没配key时不请求(monkeypatch):
    monkeypatch.setattr(embedder, "endpoint", lambda: ("", ""))
    assert embedder.configured() is False
    assert embedder.embed(["内容"]) is None


def _unit(*vals):
    n = math.sqrt(sum(v * v for v in vals))
    return [v / n for v in vals]


def test_索引存读往返(tmp_index, monkeypatch):
    docs = [
        {"id": "杭州|spot|西湖", "kind": "spot", "city": "杭州", "name": "西湖",
         "text": "t1", "meta": {"ticket_price": 0}},
        {"id": "北京|spot|故宫", "kind": "spot", "city": "北京", "name": "故宫", "text": "t2", "meta": {}},
    ]
    save_index(Index(docs, [_unit(1, 0, 0), _unit(0, 1, 0)]))
    back = load_index()
    assert back.dim == 3
    # 文档按 id 排序取回，顺序不再依赖写入次序
    assert [d["id"] for d in back.docs] == sorted(d["id"] for d in docs)
    assert [d["text"] for d in back.docs] == ["t2", "t1"]
    assert back.docs[1]["meta"] == {"ticket_price": 0}, "meta 是 JSON 字段，要原样取回"
    assert back.vectors is None, "向量留在 Milvus 里，不该跟着文档一起进内存"
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(1, 0, 0))
    hits = Retriever().search("西湖", city="杭州", min_score=0.5)["hits"]
    assert [h["id"] for h in hits] == ["杭州|spot|西湖"], "向量确实写进集合了"


def test_没有索引时返回None(tmp_index):
    assert load_index() is None


def test_索引是后来才建的也会被重新尝试(tmp_index, monkeypatch):
    """部署顺序错了（先起后端、后跑 build_kb）或容器重启，都不能让进程永久卡在关键词。"""
    docs = [{"id": "杭州|spot|西湖", "kind": "spot", "city": "杭州", "name": "西湖",
             "text": "t", "meta": {}}]
    r = Retriever()
    assert r.index is None, "此刻集合还不存在"
    save_index(Index(docs, [_unit(1, 0)]))
    assert r.index is None, "没到重试窗口之前不该偷偷换索引"
    r._retry_deadline = 0.0  # 生产中是 _CONNECT_RETRY_AFTER 秒后自动到点
    assert r.index is not None, "到点必须重新尝试载入"


def test_存储层连不上时不抛异常且退回关键词(tmp_path, monkeypatch):
    """原用例「索引文件被半写过就视为损坏」的等价场景：存储层拿不到就不能影响主链路。"""
    from app.config import settings

    monkeypatch.setattr(settings, "kb_milvus_uri", (tmp_path / "missing_dir" / "kb.db").as_posix())
    monkeypatch.setattr(settings, "kb_milvus_collection", "kb_test")
    retriever.reset_caches()
    try:
        r = Retriever()
        assert r.index is None
        assert r.search("西湖怎么玩", city="杭州")["mode"] == "keyword"
    finally:
        retriever.reset_caches()


def test_换embedding模型后维度不符会重建集合(tmp_index):
    docs = [{"id": "杭州|spot|西湖", "kind": "spot", "city": "杭州", "name": "西湖",
             "text": "t", "meta": {}}]
    save_index(Index(docs, [_unit(1, 0)]))
    assert load_index().dim == 2
    save_index(Index(docs, [_unit(1, 0, 0)]))
    back = load_index()
    assert back.dim == 3, "旧维度的向量混在里面只会算出无意义的分数，必须整集合重建"
    assert len(back) == 1


def test_删掉语料后重建索引不再召回(tmp_index, monkeypatch):
    a = {"id": "杭州|spot|西湖", "kind": "spot", "city": "杭州", "name": "西湖", "text": "t1", "meta": {}}
    b = {"id": "杭州|spot|断桥", "kind": "spot", "city": "杭州", "name": "断桥", "text": "t2", "meta": {}}
    save_index(Index([a, b], [_unit(1, 0), _unit(0, 1)]))
    save_index(Index([a], [_unit(1, 0)]))
    assert [d["id"] for d in load_index().docs] == ["杭州|spot|西湖"]
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(0, 1))
    hits = Retriever().search("断桥残雪", city="杭州", min_score=0.1)["hits"]
    assert hits == [], "断桥若还留在集合里，这条会以 1.0 分命中"


def test_城市名里的引号不能绕过city过滤(tmp_index, monkeypatch):
    """filter 是字符串拼接（milvus-lite 不支持参数化 filter），入参里的引号必须转义。"""
    docs = [
        {"id": "杭州|spot|西湖", "kind": "spot", "city": "杭州", "name": "西湖", "text": "t1", "meta": {}},
        {"id": "北京|spot|故宫", "kind": "spot", "city": "北京", "name": "故宫", "text": "t2", "meta": {}},
    ]
    save_index(Index(docs, [_unit(1, 0), _unit(0.99, 0.12)]))
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(1, 0))
    r = Retriever()
    evil = '杭州" or city == "北京'
    out = r.search("西湖", city=evil, min_score=0.1)
    assert out["hits"] == [], "未转义时这条表达式会同时命中两城，等于绕过城市硬过滤"


def test_城市过滤挡住跨城串味(tmp_index, monkeypatch):
    docs = [
        {"id": "杭州|spot|灵隐寺", "kind": "spot", "city": "杭州", "name": "灵隐寺",
         "text": "杭州·灵隐寺：需先购飞来峰景区票", "meta": {}},
        {"id": "北京|spot|故宫", "kind": "spot", "city": "北京", "name": "故宫",
         "text": "北京故宫：周一闭馆，需提前7天预约", "meta": {}},
    ]
    # 两个"预约"文档向量刻意做得几乎一样近
    near = _unit(0.99, 0.12)
    idx = Index(docs, [near, _unit(0.98, 0.2)])
    save_index(idx)
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(1.0, 0.0))

    r = Retriever()
    got = r.search("需要预约吗", city="杭州", top_k=5, min_score=0.5)
    assert got["mode"] == "vector"
    assert [h["name"] for h in got["hits"]] == ["灵隐寺"], "指定城市后绝不能召回北京文档"

    nofilter = r.search("需要预约吗", city=None, top_k=5, min_score=0.5)
    assert {h["city"] for h in nofilter["hits"]} == {"杭州", "北京"}, "不带过滤时故宫确实会串进来"


def _vec(score):
    """构造与 query=[1,0] 点积恰为 score 的单位向量。"""
    return _unit(score, math.sqrt(max(0.0, 1 - score * score)))


def test_弱命中必须被问题点名才采信(tmp_index, monkeypatch):
    """实测缺陷：语料没有迪士尼时，「上海迪士尼要预约吗」会召回上海博物馆 0.628。
    分数过线但实体不对齐，就是纯噪音；而「晚上吃什么」这种不含专名的问法召回普遍 ≥0.65，
    所以用「高分 或 被点名」双条件，两件事都能分开。"""
    docs = [
        {"id": "西安|spot|西安城墙", "kind": "spot", "city": "西安", "name": "西安城墙", "text": "t", "meta": {}},
        {"id": "上海|spot|外滩", "kind": "spot", "city": "上海", "name": "外滩", "text": "t", "meta": {}},
        {"id": "杭州|spot|灵隐寺", "kind": "spot", "city": "杭州", "name": "灵隐寺", "text": "t", "meta": {}},
    ]
    save_index(Index(docs, [_vec(0.62), _vec(0.70), _vec(0.58)]))
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(1, 0))
    hits = Retriever().search("灵隐寺要预约吗", city=None, top_k=5, min_score=0.55)["hits"]
    assert {h["name"] for h in hits} == {"外滩", "灵隐寺"}
    assert "西安城墙" not in {h["name"] for h in hits}, "0.62 且没被点名，不该当依据"


def test_复合名用片段命中也算对齐(tmp_index, monkeypatch):
    docs = [{"id": "南京|spot|夫子庙·秦淮河", "kind": "spot", "city": "南京",
             "name": "夫子庙·秦淮河", "text": "t", "meta": {}}]
    save_index(Index(docs, [_vec(0.60)]))
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(1, 0))
    hits = Retriever().search("夫子庙晚上值得去吗", city="南京", min_score=0.55)["hits"]
    assert len(hits) == 1, "用户说「夫子庙」就该命中「夫子庙·秦淮河」"


def test_name_tokens切复合名():
    from kb.retriever import name_tokens

    assert "夫子庙" in name_tokens("夫子庙·秦淮河")
    assert "先锋书店" in name_tokens("先锋书店(五台山)")
    assert name_tokens("") == []


def test_没锁定城市时阈值更严(tmp_index, monkeypatch):
    """实测缺陷：无城市过滤时「北京八达岭预约」会召回西安兵马俑(0.592)、上海博物馆(0.573)。
    这类弱命中只是碰过了 0.55 的线，送进模型纯属浪费 token 且增加幻觉风险。"""
    docs = [{"id": "西安|spot|兵马俑", "kind": "spot", "city": "西安", "name": "兵马俑", "text": "t", "meta": {}}]
    save_index(Index(docs, [_unit(0.6, 0.8)]))
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(1, 0))
    r = Retriever()

    no_city = r.search("八达岭要预约吗")
    assert no_city["min_score"] == retriever.MIN_SCORE_NO_CITY
    assert no_city["hits"] == [], "0.60 的分数在无过滤场景下不该算有效依据"

    with_city = r.search("兵马俑要看什么", city="西安")
    assert with_city["min_score"] == retriever.MIN_SCORE
    assert len(with_city["hits"]) == 1


def test_简称前缀算对齐但通用词不算():
    """C1 扩城市后实测暴露：文档叫「故宫博物院」、用户问「北京故宫周一开门吗」，
    单向包含判成未对齐，导致 0 命中。前缀简称才是中文景点的常态。
    """
    from kb.retriever import is_aligned

    assert is_aligned({"name": "故宫博物院"}, "北京故宫周一开门吗")
    assert is_aligned({"name": "天门山国家森林公园"}, "天门山要预约吗")
    assert not is_aligned({"name": "天坛公园"}, "哪个公园适合带孩子"), "通用后缀词不该被当成点名"
    assert not is_aligned({"name": "上海博物馆"}, "杭州有什么博物馆")


def test_索引扩容后简称提问能命中真实景点(tmp_index, monkeypatch):
    docs = [{"id": "北京|spot|故宫博物院", "kind": "spot", "city": "北京",
             "name": "故宫博物院", "text": "北京·故宫博物院；世界遗产；周一闭馆", "meta": {}}]
    save_index(Index(docs, [_vec(0.60)]))  # 低分：只有被点名才该采信
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(1, 0))
    hits = Retriever().search("北京故宫周一开门吗", city="北京", min_score=0.55)["hits"]
    assert hits and hits[0]["name"] == "故宫博物院"


def test_分数低于阈值被丢弃(tmp_index, monkeypatch):
    docs = [{"id": "a", "kind": "spot", "city": "杭州", "name": "A", "text": "t", "meta": {}},
            {"id": "b", "kind": "spot", "city": "杭州", "name": "B", "text": "t", "meta": {}}]
    save_index(Index(docs, [_unit(1, 0), _unit(0, 1)]))
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(0.7, 0.7))
    hits = Retriever().search("q", city="杭州", top_k=5, min_score=0.9)["hits"]
    assert hits == []


def test_关键词退路也遵守城市过滤(docs):
    hits = keyword_search(docs, "西湖", city="杭州", top_k=3)
    assert hits and all(h["city"] == "杭州" for h in hits)
    assert hits[0]["name"] == "西湖"
    assert keyword_search(docs, "", city="杭州") == []


def test_无索引时不抛异常(tmp_index, monkeypatch):
    monkeypatch.setattr(Retriever, "docs", property(lambda self: []))
    out = Retriever().search("西湖怎么玩", city="杭州")
    assert out["mode"] == "keyword"
    assert out["hits"] == []
    assert Retriever().search("   ")["mode"] == "none"


def test_topk被夹在合理区间(tmp_index, monkeypatch):
    docs = [{"id": f"杭州|spot|S{i}", "kind": "spot", "city": "杭州", "name": f"S{i}", "text": "t", "meta": {}}
            for i in range(30)]
    save_index(Index(docs, [_unit(1, 0) for _ in docs]))
    monkeypatch.setattr(embedder, "embed_one", lambda q: _unit(1, 0))
    assert len(Retriever().search("q", city="杭州", top_k=999)["hits"]) == 20

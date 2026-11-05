"""P2 问答接检索：验证「查不到就不让模型答」这条纪律。

这几条测试的核心不是答案质量，而是**调用顺序**：
检索为空时必须直接拒答、绝不能把裸问题丢给 LLM——否则前面做的检索等于白做。
全部离线，用假检索和假 LLM。
"""
import asyncio

import pytest

from app.config import settings
from app.services import chat_service as cs
from app.services.chat_service import REFUSAL, SYSTEM_RULE, build_prompt
from app.services.chat_service import chat_service
from kb.retriever import detect_city

HITS = [
    {"id": "杭州|spot|灵隐寺", "city": "杭州", "name": "灵隐寺", "kind": "spot", "score": 0.71,
     "text": "杭州·灵隐寺；人文历史；需先买飞来峰门票再入寺；门票约75元；需要提前预约", "meta": {}},
    {"id": "杭州|spot|西湖", "city": "杭州", "name": "西湖", "kind": "spot", "score": 0.62,
     "text": "杭州·西湖；自然风光；门票免费；建议游玩180分钟", "meta": {}},
]


@pytest.fixture
def reset_stats():
    before = dict(chat_service.stats)
    yield
    chat_service.stats.clear()
    chat_service.stats.update(before)


@pytest.fixture
def fake_llm(monkeypatch):
    """记录送进模型的 prompt，方便断言「资料确实带上了」。"""
    box = {"prompts": [], "answer": "灵隐寺需先购飞来峰景区门票，再买寺内香花券。", "stream": False}

    async def _gen(prompt):
        box["prompts"].append(prompt)
        return box["answer"]

    async def _stream(prompt):
        box["prompts"].append(prompt)
        box["stream"] = True
        if box["answer"]:
            yield box["answer"]

    monkeypatch.setattr(cs.llm_client, "generate_text", _gen)
    monkeypatch.setattr(cs.llm_client, "generate_text_stream", _stream)
    return box


@pytest.fixture
def fake_search(monkeypatch):
    def _install(hits, city_seen=None):
        def _search(query, city=None, top_k=5, min_score=0.55):
            if city_seen is not None:
                city_seen["city"] = city
                city_seen["top_k"] = top_k
            return {"mode": "vector", "hits": hits, "query": query, "filtered_city": city}

        monkeypatch.setattr(cs.retriever, "search", _search)
    return _install


def _run(coro):
    return asyncio.run(coro)


def _collect(gen):
    async def _go():
        return [c async for c in gen]
    return _run(_go())


@pytest.mark.parametrize("q,expect", [
    ("杭州灵隐寺要预约吗", "杭州"),
    ("这趟高铁到上海虹桥", "上海"),
    ("拙政园几点开门", "苏州"),
    ("灵隐寺要不要预约", "杭州"),
    ("夜游夫子庙去哪个城市", "南京"),
    ("洪崖洞几点看夜景最好", "重庆"),
    ("太古里逛街要预约吗", "成都"),
    ("帮我看看行程怎么安排", None),
    ("", None),
])
def test_城市锁定优先城市名其次景点名反查(q, expect):
    """用户基本不写城市名，但会写景点名——不反查的话城市过滤形同虚设。

    复合名（夫子庙·秦淮河）还要能被简写命中，所以别名切分也是必须的。
    """
    assert detect_city(q) == expect


def test_检索为空时直接拒答且不问模型(monkeypatch, fake_search, reset_stats):
    calls = []

    async def _never(prompt):
        calls.append(prompt)
        return "编造的答案"

    monkeypatch.setattr(cs.llm_client, "generate_text", _never)
    monkeypatch.setattr(settings, "llm_api_key", "fake-key")
    fake_search([])
    out = _run(chat_service.qa("珠峰大本营门票多少钱"))
    assert out == REFUSAL
    assert calls == [], "检索没命中却仍去问模型，等于把幻觉风险放回链路"
    assert chat_service.stats["refused"] == 1


def test_有资料时把资料塞进prompt再问模型(fake_llm, fake_search, monkeypatch, reset_stats):
    monkeypatch.setattr(settings, "llm_api_key", "fake-key")
    fake_search(HITS)
    out = _run(chat_service.qa("灵隐寺要预约吗"))
    assert out == fake_llm["answer"]
    prompt = fake_llm["prompts"][0]
    assert SYSTEM_RULE in prompt
    assert "需先买飞来峰门票" in prompt, "检索到的事实必须出现在 prompt 里"
    assert "灵隐寺要预约吗" in prompt
    assert chat_service.stats["with_context"] == 1


def test_问题里的城市会转成检索过滤(fake_search, monkeypatch, reset_stats):
    seen = {}
    monkeypatch.setattr(settings, "llm_api_key", "")
    fake_search(HITS, seen)
    _run(chat_service.qa("杭州灵隐寺要预约吗"))
    assert seen["city"] == "杭州", "不带城市过滤就会召回别的城市的同类规则"

    seen2 = {}
    fake_search(HITS, seen2)
    _run(chat_service.qa("第一次出国要准备什么"))
    assert seen2["city"] is None, "识别不出城市时宁可不筛选，别把有效召回误杀"


def test_没有LLMKey时回资料原文而不是套话(fake_search, monkeypatch, reset_stats):
    monkeypatch.setattr(settings, "llm_api_key", "")
    fake_search(HITS)
    out = _run(chat_service.qa("灵隐寺要预约吗"))
    assert out.startswith("根据本地景点库：")
    assert "灵隐寺" in out
    assert chat_service.stats["corpus_fallback"] == 1


def test_模型返回空也要退回资料(fake_llm, fake_search, monkeypatch, reset_stats):
    monkeypatch.setattr(settings, "llm_api_key", "fake-key")
    fake_llm["answer"] = ""
    fake_search(HITS)
    out = _run(chat_service.qa("灵隐寺要预约吗"))
    assert out.startswith("根据本地景点库："), "模型空返回不能给用户一片空白"
    assert chat_service.stats["corpus_fallback"] == 1


def test_流式同样遵守拒答纪律(fake_llm, fake_search, monkeypatch, reset_stats):
    monkeypatch.setattr(settings, "llm_api_key", "fake-key")
    fake_search([])
    assert "".join(_collect(chat_service.qa_stream("珠峰怎么去"))) == REFUSAL
    assert fake_llm["prompts"] == []

    fake_search(HITS)
    chunks = _collect(chat_service.qa_stream("灵隐寺要预约吗"))
    assert "".join(chunks) == fake_llm["answer"]
    assert "需先买飞来峰门票" in fake_llm["prompts"][-1]


def test_流式无LLM时分片回资料(fake_search, monkeypatch, reset_stats):
    monkeypatch.setattr(settings, "llm_api_key", "")
    fake_search(HITS)
    text = "".join(_collect(chat_service.qa_stream("灵隐寺要预约吗")))
    assert text.startswith("根据本地景点库：")


def test_build_prompt限制上下文体积():
    fat = [{"text": "字" * 800, "city": "杭州", "name": "x", "kind": "spot", "score": 0.9, "id": "x", "meta": {}}
           for _ in range(10)]
    prompt = build_prompt("q", fat)
    assert len(prompt) < 1500, "上下文不封顶，长语料会把 token 成本和延迟一起打爆"


def test_比率统计口径一致(fake_search, monkeypatch, reset_stats):
    monkeypatch.setattr(settings, "llm_api_key", "")
    fake_search(HITS)
    _run(chat_service.qa("杭州灵隐寺"))
    st = chat_service.rag_stats()
    assert st["asked"] == 1
    assert st["grounded_rate"] == 1.0
    assert st["refusal_rate"] == 0
    assert st["retriever"]["docs"] > 0


def test_统计接口已注册(client, auth):
    r = client.get("/api/chat/rag_stats", headers=auth)
    assert r.status_code == 200
    body = r.json()["data"]
    for k in ("asked", "with_context", "refused", "grounded_rate", "refusal_rate", "retriever"):
        assert k in body


def test_旧版硬编码套话已删除():
    """原来无 Key 时靠 if "西湖" 写死答案，现在必须走检索，不再存在这条代码路径。"""
    import app.services.chat_service as m

    assert not hasattr(m, "_fake_qa")
    src = open(m.__file__, encoding="utf-8").read()
    assert "西湖全天免费开放" not in src

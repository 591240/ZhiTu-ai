"""问答服务：先检索，再让模型基于资料作答；检索不到就直接拒答。

顺序是关键：不是「模型答不上再查」，而是「查不到就不让模型答」。
行程类产品最伤信任的是编造开放时间、票价、预约规则，这类事实宁可拒答。
"""
import logging
import re
from datetime import date

from fastapi.concurrency import run_in_threadpool

from app.ai.llm_client import llm_client
from app.config import settings
from kb.retriever import detect_city, retriever

logger = logging.getLogger(__name__)

MAX_HITS = 4
CONTEXT_MAX_CHARS = 1200
REFUSAL = "这个我没查到可靠资料，建议以景区官方公告为准。可以换个说法，或带上城市和景点名再问我一次。"
SYSTEM_RULE = (
    "只能依据【资料】回答。资料里没有的开放时间、门票价格、预约规则、地址，"
    "一律回答「资料未收录」，禁止凭常识补全。80字内，直接给结论，不要复述问题。"
)


def _chunk(text: str):
    """把整段文字按标点切小片，模拟流式输出。"""
    parts = re.split(r"(?<=[。！？])", text)
    return [p for p in parts if p]


def _context(hits: list[dict]) -> str:
    lines, used = [], 0
    for i, h in enumerate(hits, 1):
        line = f"{i}. {h['text']}"
        if used + len(line) > CONTEXT_MAX_CHARS:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)


def build_prompt(question: str, hits: list[dict]) -> str:
    return f"{SYSTEM_RULE}\n\n【资料】\n{_context(hits)}\n\n【问题】{question}"


def _from_corpus(hits: list[dict]) -> str:
    """没有 LLM Key 时的诚实退路：把检索到的事实原样回给用户，而不是给一段写死的套话。"""
    facts = []
    for h in hits[:2]:
        segs = [s for s in h["text"].split("；") if not s.startswith("适合")]
        facts.append("；".join(segs[:3]))
    return "根据本地景点库：" + " / ".join(facts)


class ChatService:
    def __init__(self):
        # 可观测性：简历/答辩能说出「无依据拒答率」是怎么来的，靠的就是这几个计数。
        # ⚠️ 这是**进程内**计数：多 worker 部署时 /api/chat/rag_stats 只反映当前进程，
        # 全量数字会偏小。要精确统计得把这几个数迁 Redis（代价是每次问答多两次往返，
        # 当前规模不值得）。单 worker（compose 默认）下数字是准的。
        self.stats = {"asked": 0, "with_context": 0, "refused": 0, "corpus_fallback": 0, "keyword_mode": 0}

    def retrieve(self, question: str) -> dict:
        res = retriever.search(question, city=detect_city(question), top_k=MAX_HITS)
        if res.get("mode") == "keyword":
            self.stats["keyword_mode"] += 1
        return res

    async def _retrieve_async(self, question: str) -> dict:
        """检索内部要打 embedding 接口（同步 requests），必须挪出事件循环。"""
        return await run_in_threadpool(self.retrieve, question)

    async def qa(self, question: str) -> str:
        self.stats["asked"] += 1
        hits = (await self._retrieve_async(question))["hits"]
        if not hits:
            self.stats["refused"] += 1
            return REFUSAL
        self.stats["with_context"] += 1
        if settings.llm_api_key:
            ans = await llm_client.generate_text(build_prompt(question, hits))
            if ans:
                return ans
            logger.info("LLM 未返回内容，退回资料原文")
        self.stats["corpus_fallback"] += 1
        return _from_corpus(hits)

    async def qa_stream(self, question: str):
        """流式回答：检索为空就流拒答文案；有资料则带上下文流式生成。"""
        self.stats["asked"] += 1
        hits = (await self._retrieve_async(question))["hits"]
        if not hits:
            self.stats["refused"] += 1
            for piece in _chunk(REFUSAL):
                yield piece
            return
        self.stats["with_context"] += 1
        if settings.llm_api_key:
            got = False
            async for tok in llm_client.generate_text_stream(build_prompt(question, hits)):
                got = True
                yield tok
            if got:
                return
            logger.info("LLM 流式无输出，退回资料原文")
        self.stats["corpus_fallback"] += 1
        for piece in _chunk(_from_corpus(hits)):
            yield piece

    def rag_stats(self) -> dict:
        out = dict(self.stats)
        total = out["asked"]
        out["refusal_rate"] = round(out["refused"] / total, 4) if total else 0
        out["grounded_rate"] = round(out["with_context"] / total, 4) if total else 0
        out["retriever"] = retriever.status()
        return out

    async def luggage(self, city: str = "", days: int = 2, season: str = "") -> dict:
        """行李清单：按天数/季节/目的地做真实分支，不再是写死的四组通用清单。"""
        days = max(1, min(int(days or 2), 15))
        city = (city or "").strip()
        season = (season or "").strip()
        if not season:
            month = date.today().month
            season = "冬" if month in (12, 1, 2) else "春" if month in (3, 4, 5) \
                else "夏" if month in (6, 7, 8) else "秋"

        clothes = ["外套", "舒适运动鞋", "换洗衣物"]
        if days >= 3:
            clothes.append(f"换洗内衣 ×{min(days, 7)}")
        if "夏" in season:
            clothes = ["速干短袖", "防晒衣", "遮阳帽", "凉鞋/透气运动鞋"]
        elif "冬" in season:
            clothes = ["羽绒服/厚外套", "保暖内衣", "围巾手套", "防滑保暖鞋"]
        elif "春" in season or "秋" in season:
            clothes = ["薄外套", "长袖上衣", "长裤", "舒适运动鞋"]

        toiletries = ["牙刷牙膏", "护肤品"]
        toiletries.append("防晒霜 SPF50+" if "夏" in season else "润唇膏/保湿霜")

        electronics = ["充电宝", "数据线", "耳机"]
        if days >= 3:
            electronics.append("多口充电头")

        meds = ["创可贴", "肠胃药"]
        if "夏" in season:
            meds += ["藿香正气/防暑药", "驱蚊液"]
        if "冬" in season:
            meds += ["感冒药", "暖宝宝"]

        docs = ["身份证", "手机（健康码/乘车码）"]
        if any(k in city for k in ("香港", "澳门")):
            docs = ["港澳通行证及有效签注", "身份证", "少量港币/澳门元现金", "英标转换插头"]
        elif "台湾" in city:
            docs = ["大通证 + 入台证", "身份证", "新台币现金", "美标转换插头"]
        elif city and not any(k in city for k in ("省", "市")) and len(city) <= 4:
            # 国内城市默认；出境城市由上面的分支覆盖
            docs = ["身份证", "手机（乘车码/门票码）"]

        return {"list": [
            {"group": "证件", "items": docs},
            {"group": "衣物", "items": clothes},
            {"group": "洗漱", "items": toiletries},
            {"group": "电子", "items": electronics},
            {"group": "药品", "items": meds},
        ]}

    async def food(self, city: str) -> dict:
        return {
            "red": [f"{city or '当地'}老字号餐馆", "夜市人气小吃", "景区外居民区餐厅"],
            "black": ["景区内高价套餐", "拉客低价团餐", "无明码标价大排档"],
        }


chat_service = ChatService()

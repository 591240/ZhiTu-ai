"""检索层：city 硬过滤（下推成 Milvus filter）→ 向量 top-k → 分数/实体双闸门；拿不到就退回关键词。

向量存在 Milvus（pymilvus MilvusClient），文档元数据在载入时一次性取进内存：
detect_city 和关键词退路都要靠全量文档，而它只有几百 KB，向量才是大头。

city 硬过滤为什么要在打分之前做：实测「问灵隐寺要不要预约」的语义近邻第二名是**北京故宫**——
串味是语义层面的，调阈值调不掉，只能靠 city 在打分之前排除。这条过滤比换不换存储引擎重要得多。

filter 里的 city 是用户可控入参（`routers/kb.py` 直接收 query 参数），而 milvus-lite 不支持
`filter_template_values` 参数化（实测报 unexpected character '{'），所以字符串字面量必须自己转义：
实测未转义的 `杭州" or city == "北京` 会同时命中两城，等于绕过城市过滤。
"""
import logging
import re
import time
from pathlib import Path

from app.config import settings
from kb import corpus, embedder

logger = logging.getLogger(__name__)

SERVER_DIR = Path(__file__).resolve().parents[1]

MIN_SCORE = 0.55
# 没锁定城市时提高门槛：实测「北京八达岭要不要预约」会在无过滤下召回
# 西安兵马俑 0.592、上海博物馆 0.573——都过了 0.55，却全是无效上下文。
MIN_SCORE_NO_CITY = 0.65
# 实体对齐线：分数够不到这里，就必须问题里点名了该景点才肯用。
# 依据实测——「上海迪士尼」在无该语料时召回到最高 0.628 的无关条目，
# 而「晚上吃什么」这类不含专名的正常问法召回普遍 ≥0.656，两条线刚好能分开。
STRONG_SCORE = 0.65
DEFAULT_TOP_K = 5

VECTOR_FIELD = "vector"
DOC_FIELDS = ("id", "city", "name", "kind", "text", "meta")
# VARCHAR 的 max_length 按字节算，中文一字 3 字节，所以按 UTF-8 上限放宽。
MAX_LEN = {"id": 512, "city": 128, "name": 512, "kind": 64, "text": 16384}
UPSERT_BATCH = 100
# 单次调用超时。这个数就是 Milvus 卡死时用户要多等的时间（之后退回关键词），所以压到 10s：
# 实测健康集合一次检索 3.5~30 ms，10s 已经是三个数量级的余量。
MILVUS_TIMEOUT = 10.0
QUERY_LIMIT_MAX = 16384


class Index:
    """文档集句柄。vectors 只在 build→save 之间短暂存在，检索阶段向量留在 Milvus 里。"""

    def __init__(self, docs: list[dict], vectors: list[list[float]] | None = None, dim: int = 0):
        if vectors is not None and len(docs) != len(vectors):
            raise ValueError("文档数与向量数不一致，索引已损坏，请重跑 build_kb")
        self.docs = docs
        self.vectors = vectors
        if vectors is not None:
            self.dim = len(vectors[0]) if vectors else 0
        else:
            self.dim = dim

    def __len__(self):
        return len(self.docs)


# ---------------------------------------------------------------- Milvus 连接

_client = None
# 下一次允许重试连接的时间点（time.monotonic 基准）；0 = 立即可试。
_client_deadline = 0.0
# 连不上不能永久放弃：milvus 容器重启是分钟级的事，永久降级等于一次抖动废掉整个进程。
_CONNECT_RETRY_AFTER = 60.0


def _uri() -> str:
    """Milvus 连接串：http(s):// 原样用；文件路径一律按后端目录解析。

    按 CWD 解析的话，uvicorn 从仓库根启动和从 server/ 启动会指向两个不同的库，
    而路径写错不会报错——只会静默退回关键词匹配，很难查出来。
    """
    raw = (settings.kb_milvus_uri or "").strip()
    if not raw or raw.startswith(("http://", "https://")):
        return raw
    p = Path(raw)
    return str(p if p.is_absolute() else SERVER_DIR / p)


def _collection() -> str:
    return (settings.kb_milvus_collection or "kb_docs").strip()


def collection_name() -> str:
    """给 scripts/build_kb.py 打印用；内部一律走 _collection()。"""
    return _collection()


def client():
    """懒建连接；未配置、没装 pymilvus、连不上都返回 None，由调用方决定退路。

    连不上不是永久放弃：milvus 容器重启是分钟级的事，一次抖动就把进程锁死在关键词
    模式上，比慢几十毫秒严重得多。失败后隔 _CONNECT_RETRY_AFTER 再试一次。
    """
    global _client, _client_deadline
    if not _uri():
        return None
    if _client is not None:
        return _client
    if time.monotonic() < _client_deadline:
        return None
    try:
        from pymilvus import MilvusClient
    except ImportError:
        logger.warning("未安装 pymilvus，向量检索不可用（pip install pymilvus）")
        _client_deadline = time.monotonic() + _CONNECT_RETRY_AFTER
        return None
    kwargs = {"timeout": MILVUS_TIMEOUT}
    if settings.kb_milvus_token:
        kwargs["token"] = settings.kb_milvus_token
    try:
        cl = MilvusClient(_uri(), **kwargs)
        cl.list_collections()  # 立刻验活，别让每次检索都白等一轮超时
    except Exception as e:
        _client_deadline = time.monotonic() + _CONNECT_RETRY_AFTER
        logger.warning("Milvus 不可用（%s: %s），检索退回关键词匹配，%.0f 秒后重试",
                       type(e).__name__, str(e)[:160], _CONNECT_RETRY_AFTER)
        return None
    _client = cl
    _client_deadline = 0.0
    logger.info("Milvus 已连接 uri=%s collection=%s", _uri(), _collection())
    return cl


def close_client() -> None:
    """换 uri / 换集合（测试每个用例指向自己的临时库）后必须丢掉旧连接。"""
    global _client, _client_deadline
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _client_deadline = 0.0


def _literal(value) -> str:
    """转义成 Milvus 字符串字面量内容：先转反斜杠再转双引号，顺序颠倒会留后门。"""
    s = "" if value is None else str(value)
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _in_list(values) -> str:
    return "[" + ", ".join(f'"{_literal(v)}"' for v in values) + "]"


# ---------------------------------------------------------------- 索引读写

def build_documents() -> list[dict]:
    return corpus.build_docs()


def build_index(docs: list[dict]) -> Index:
    vectors = embedder.embed([d["text"] for d in docs])
    if vectors is None:
        raise RuntimeError("embedding 服务不可用，无法建索引")
    return Index(docs, vectors)


def _collection_dim(cl, name: str) -> int | None:
    """取集合向量维度；取不到返回 None（区别于"确实是 0"），让调用方跳过一致性校验。"""
    try:
        desc = cl.describe_collection(name)
        for f in (desc.get("fields") or []):
            if f.get("name") == VECTOR_FIELD:
                dim = (f.get("params") or {}).get("dim")
                return int(dim) if dim else None
    except Exception as e:
        logger.info("describe_collection 不可用（%s），跳过维度校验", str(e)[:100])
    return None


def _ensure_collection(cl, name: str, dim: int) -> None:
    if cl.has_collection(name):
        cur = _collection_dim(cl, name)
        if cur and cur != dim:
            # 换 embedding 模型后维度必变，旧向量混在里面只会算出无意义的分数。
            logger.warning("集合维度 %s 与当前 %s 不符，重建集合 %s", cur, dim, name)
            cl.drop_collection(name)
        else:
            return
    from pymilvus import DataType

    schema = cl.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=MAX_LEN["id"])
    schema.add_field(VECTOR_FIELD, DataType.FLOAT_VECTOR, dim=dim)
    schema.add_field("city", DataType.VARCHAR, max_length=MAX_LEN["city"])
    schema.add_field("name", DataType.VARCHAR, max_length=MAX_LEN["name"])
    schema.add_field("kind", DataType.VARCHAR, max_length=MAX_LEN["kind"])
    schema.add_field("text", DataType.VARCHAR, max_length=MAX_LEN["text"])
    schema.add_field("meta", DataType.JSON)
    params = cl.prepare_index_params()
    # FLAT = 精确检索：几百条量级不值得为近似索引引入召回误差。
    params.add_index(field_name=VECTOR_FIELD, index_type="FLAT", metric_type="COSINE")
    cl.create_collection(name, schema=schema, index_params=params)


def save_index(index: Index) -> None:
    """写入 Milvus。建索引是显式操作，失败要抛出来，不能像检索那样静默退化成关键词。"""
    if index.vectors is None:
        raise ValueError("没有向量可写，请先 build_index")
    cl = client()
    if cl is None:
        raise RuntimeError("Milvus 未就绪（检查 KB_MILVUS_URI 与 pymilvus 是否安装），索引无法写入")
    name = _collection()
    _ensure_collection(cl, name, index.dim)
    rows = [{"id": d["id"], VECTOR_FIELD: v, "city": d.get("city") or "",
             "name": d.get("name") or "", "kind": d.get("kind") or "",
             "text": d.get("text") or "", "meta": d.get("meta") or {}}
            for d, v in zip(index.docs, index.vectors)]
    for i in range(0, len(rows), UPSERT_BATCH):
        cl.upsert(name, rows[i:i + UPSERT_BATCH])
    # 删掉这次文档集里已经不存在的行，否则语料删了景点还能被召回。
    keep = {d["id"] for d in index.docs}
    existing = {r["id"] for r in cl.query(name, filter='id != ""',
                                         output_fields=["id"], limit=QUERY_LIMIT_MAX)}
    stale = sorted(existing - keep)
    if stale:
        cl.delete(name, filter=f"id in {_in_list(stale)}")
        logger.info("清理已删除的文档 %d 条", len(stale))
    cl.load_collection(name)


def fetch_docs(cl, name: str) -> list[dict]:
    """取回全部文档元数据（不含向量），按 id 排序保证多次载入的顺序稳定。"""
    rows = cl.query(name, filter='id != ""', output_fields=list(DOC_FIELDS),
                    limit=QUERY_LIMIT_MAX)
    docs = [{"id": r["id"], "city": r.get("city") or "", "name": r.get("name") or "",
             "kind": r.get("kind") or "", "text": r.get("text") or "",
             "meta": r.get("meta") or {}} for r in rows]
    docs.sort(key=lambda d: d["id"])
    return docs


def _probe_dim(cl, name: str) -> int:
    dim = _collection_dim(cl, name)
    if dim:
        return dim
    one = cl.query(name, filter='id != ""', limit=1, output_fields=[VECTOR_FIELD])
    if one and one[0].get(VECTOR_FIELD):
        return len(one[0][VECTOR_FIELD])
    return 0


def load_index() -> Index | None:
    cl = client()
    if cl is None:
        return None
    name = _collection()
    try:
        if not cl.has_collection(name):
            return None
        cl.load_collection(name)
        docs = fetch_docs(cl, name)
        if not docs:
            return None
        return Index(docs, dim=_probe_dim(cl, name))
    except Exception as e:
        logger.warning("从 Milvus 载入文档失败（%s: %s），退回关键词匹配",
                       type(e).__name__, str(e)[:160])
        return None


# ---------------------------------------------------------------- 城市与实体对齐

_CITY_NAMES: list[str] | None = None
_NAME_CITY: dict[str, str] | None = None


_NAME_SPLIT = re.compile(r"[·・\-—_、/｜|（）()\s]+")


def _name_index() -> dict[str, str]:
    """景点名（含别名片段）→ 所属城市。用户几乎不会在问题里写城市名，但会写景点名。

    语料里有 18 个复合名，如「夫子庙·秦淮河」「解放碑·洪崖洞」，
    只按全名匹配的话，用户说「夫子庙」就锁不到南京，所以要把分隔符切出的片段一起登记。
    """
    global _NAME_CITY
    if _NAME_CITY is None:
        m: dict[str, str] = {}
        for d in retriever.docs:
            full = (d.get("name") or "").strip()
            tokens = [full] + [t.strip() for t in _NAME_SPLIT.split(full)]
            for token in tokens:
                if len(token) >= 2:
                    m.setdefault(token, d["city"])
        _NAME_CITY = m
    return _NAME_CITY


def name_tokens(name: str) -> list[str]:
    """复合名的可匹配片段：全名 + 分隔符切出的片段（夫子庙·秦淮河 → 含「夫子庙」）。"""
    full = (name or "").strip()
    return [t for t in [full] + [x.strip() for x in _NAME_SPLIT.split(full)] if len(t) >= 2]


def is_aligned(doc: dict, query: str) -> bool:
    """问题里是否点名了这条文档。低分命中只有在被点名时才算依据。

    除了全名和复合名片段，还要认「前缀简称」：中文里故宫博物院→故宫、
    天门山国家森林公园→天门山，用户基本只写前几个字。
    只按前缀而不按任意子串，是为了不让"哪个公园适合孩子"误命中"天坛公园"。
    """
    q = query or ""
    for tok in name_tokens(doc.get("name") or ""):
        if tok in q:
            return True
        if len(tok) > 2 and any(tok[:n] in q for n in (2, 3, 4)):
            return True
    return False


def detect_city(text: str) -> str | None:
    """从问题文本里锁定城市。

    QA 请求体只有 question（前端不传城市），而串味只能靠城市硬过滤挡，
    所以这里必须先猜出城市；猜不出来就不过滤，宁可召回宽一点也不误杀。
    先按城市名匹配，匹配不到再用景点名反查——「拙政园要不要预约」这种问法最常见。
    """
    global _CITY_NAMES
    t = (text or "").strip()
    if not t:
        return None
    if _CITY_NAMES is None:
        # 从文档集取城市，而不是只取语料城市：扩了 POI 城市之后必须一起认得，
        # 否则「北京故宫要预约吗」锁不住北京，城市硬过滤等于没生效。
        _CITY_NAMES = sorted({d["city"] for d in retriever.docs if d.get("city")}, key=len, reverse=True)
    for city in _CITY_NAMES:
        if city in t:
            return city
    for name in sorted(_name_index(), key=len, reverse=True):
        if name in t:
            return _name_index()[name]
    return None


def _bigrams(text: str) -> set:
    t = "".join((text or "").split())
    return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else {t} if t else set()


def keyword_search(docs: list[dict], query: str, city: str | None = None, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """无向量时的退路：按字符二元组重合度打分，同样先按城市排除。"""
    qb = _bigrams(query)
    if not qb:
        return []
    hits = []
    for d in docs:
        if city and d.get("city") != city:
            continue
        db = _bigrams(d["text"])
        if not db:
            continue
        overlap = len(qb & db) / len(qb)
        if overlap > 0:
            hits.append(_hit(d, round(overlap, 4), "keyword"))
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:top_k]


def _hit(doc: dict, score: float, mode: str) -> dict:
    return {"id": doc["id"], "city": doc["city"], "name": doc["name"], "kind": doc["kind"],
            "score": round(float(score), 4), "text": doc["text"], "meta": doc.get("meta") or {},
            "match": mode}


# ---------------------------------------------------------------- 检索

def vector_search(index: Index, qvec: list[float], city: str | None, top_k: int,
                  min_score: float, query: str) -> list[dict]:
    """Milvus 取候选 → 分数线 → 实体对齐门 → top_k。

    limit 用的是「该城市的全部文档数」（无城市时是全量），不是 top_k：
    分数线和对齐门都在取回之后生效，只取 top_k 会把闸门本该留下的命中切掉。
    """
    cl = client()
    if cl is None:
        return []
    if city:
        pool = sum(1 for d in index.docs if d.get("city") == city)
        if pool == 0:
            return []
        expr = f'city == "{_literal(city)}"'
    else:
        pool = len(index.docs)
        expr = 'id != ""'
    limit = max(1, min(pool, QUERY_LIMIT_MAX))
    res = cl.search(_collection(), data=[qvec], filter=expr, limit=limit,
                    output_fields=list(DOC_FIELDS),
                    search_params={"metric_type": "COSINE"})
    kept = []
    for h in (res[0] if res else []):
        ent = h.get("entity") or {}
        doc = {k: ent.get(k) for k in DOC_FIELDS}
        doc["meta"] = doc.get("meta") or {}
        score = float(h.get("distance", 0.0))
        if score < min_score:
            continue
        # 弱命中只有在「问题里点名了它」时才算依据，否则就是同城随机景点
        if score < STRONG_SCORE and not is_aligned(doc, query):
            continue
        kept.append((score, doc))
    kept.sort(key=lambda x: x[0], reverse=True)
    return [_hit(d, s, "vector") for s, d in kept[:top_k]]


class Retriever:
    """懒加载索引；任何一步不成立都退化成关键词，永不抛异常。"""

    def __init__(self):
        self._index: Index | None = None
        self._tried = False
        self._docs: list[dict] | None = None
        self._retry_deadline = 0.0

    @property
    def docs(self) -> list[dict]:
        """关键词退路用的文档集：有索引就用索引（覆盖 POI 城市），否则退回语料。

        不这么做的话，扩了 POI 城市之后，退路只会认原来 9 城。
        """
        idx = self.index
        if idx:
            return idx.docs
        if self._docs is None:
            self._docs = corpus.build_docs()
        return self._docs

    @property
    def index(self) -> Index | None:
        # 一次失败不能锁死整个进程：milvus 容器重启是分钟级的事，
        # 部署顺序错了（先起 backend 后建索引）也一样，到点就该再试。
        if self._index is None and time.monotonic() >= self._retry_deadline:
            self._tried = False
        if not self._tried:
            self._index = load_index()
            self._tried = True
            self._retry_deadline = time.monotonic() + _CONNECT_RETRY_AFTER
            if self._index is None:
                logger.info("未找到检索索引，使用关键词匹配"
                            "（配好 KB_MILVUS_URI 后跑 scripts/build_kb.py 可启用向量检索）")
        return self._index

    def status(self) -> dict:
        idx = self.index
        return {
            "docs": len(self.docs),
            "indexed": bool(idx),
            "index_size": len(idx) if idx else 0,
            "dim": idx.dim if idx else 0,
            "engine": "milvus" if idx else "keyword",
            "milvus_configured": bool(_uri()),
            "embedding_configured": embedder.configured(),
        }

    def search(self, query: str, city: str | None = None, top_k: int = DEFAULT_TOP_K,
               min_score: float | None = None) -> dict:
        query = (query or "").strip()
        top_k = max(1, min(int(top_k or DEFAULT_TOP_K), 20))
        if min_score is None:
            min_score = MIN_SCORE if city else MIN_SCORE_NO_CITY
        if not query:
            return {"mode": "none", "hits": [], "filtered_city": city, "query": "", "min_score": min_score}

        idx = self.index
        if idx:
            qvec = embedder.embed_one(query)
            if qvec:
                try:
                    return {"mode": "vector", "filtered_city": city, "query": query,
                            "min_score": min_score,
                            "hits": vector_search(idx, qvec, city, top_k, min_score, query)}
                except Exception as e:
                    # Milvus 抖动不该让问答失败：退到关键词，而不是退成一个空答案。
                    logger.warning("Milvus 检索异常（%s: %s），本次退回关键词匹配",
                                   type(e).__name__, str(e)[:160])
            else:
                logger.info("query embedding 失败，本次退回关键词匹配")

        return {"mode": "keyword", "filtered_city": city, "query": query, "min_score": min_score,
                "hits": keyword_search(self.docs, query, city, top_k)}


retriever = Retriever()


def status() -> dict:
    """模块级便捷入口（与 build_index / save_index / reset_caches 同一风格）。

    实例方法叫 `Retriever.status()`，但模块名和实例名都叫 retriever，
    调用方写 `retriever.retriever.status()` 太绕——scripts/build_kb.py --status 要用。
    """
    return retriever.status()


def reset_caches() -> None:
    """重建索引后清掉派生缓存（城市名表、景点别名、已加载的索引、Milvus 连接）。

    丢连接是因为 KB_MILVUS_URI 可能刚被换掉——测试每个用例指向自己的临时库。
    """
    global _CITY_NAMES, _NAME_CITY
    _CITY_NAMES = None
    _NAME_CITY = None
    retriever._index = None
    retriever._tried = False
    retriever._docs = None
    retriever._retry_deadline = 0.0
    close_client()

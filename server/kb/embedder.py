"""Embedding 客户端：百炼 OpenAI 兼容端点，默认复用视觉模型那把 key。

三条约定，都是这轮实测出来的：
 1. 返回的 data 顺序不保证跟输入一致，必须按 index 排序后取（踩过）。
 2. 返回向量已是单位长度，但仍显式归一化一次，不依赖上游行为。
 3. 任何失败返回 None 而不是抛异常——检索拿不到向量就退回关键词匹配，
    绝不能因为 embedding 服务抖动而影响行程生成主链路。
"""
import atexit
import hashlib
import json
import logging
import math
import os
import tempfile
import time
from pathlib import Path

import requests

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent / "corpus" / "embed_cache.json"
BATCH = 10  # 实测单次 9 条通过，按 10 分批留余量；被拒时会自动降为逐条重试

# 落盘节流：缓存文件已近 3MB，之前每次有新向量就全量重写一遍，
# 每个新问题都要付一次 3MB 序列化 + 磁盘写入的代价，且并发写会互相截断写坏文件。
# 改成攒一批再落盘 + 临时文件原子替换。
_FLUSH_EVERY_N = 50
_FLUSH_EVERY_SEC = 30.0
_dirty = 0
_last_flush = 0.0


def endpoint() -> tuple[str, str]:
    url = (settings.embedding_api_url or settings.vision_api_url or "").rstrip("/")
    key = settings.embedding_api_key or settings.vision_api_key
    return url, key


def configured() -> bool:
    url, key = endpoint()
    return bool(url and key and settings.embedding_model)


def normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if not norm:
        return vec
    return [v / norm for v in vec]


def _cache_key(text: str) -> str:
    return hashlib.sha256(f"{settings.embedding_model}\n{text}".encode("utf-8")).hexdigest()


_CACHE_MEM: dict | None = None  # 缓存文件已近 3MB，每次查询都重新解析会白加几十毫秒


def _load_cache() -> dict:
    global _CACHE_MEM
    if _CACHE_MEM is None:
        try:
            _CACHE_MEM = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _CACHE_MEM = {}
    return _CACHE_MEM


def _save_cache(cache: dict) -> None:
    """更新内存缓存，并按节流策略落盘。"""
    global _CACHE_MEM, _dirty, _last_flush
    _CACHE_MEM = cache
    _dirty += 1
    now = time.time()
    if _dirty < _FLUSH_EVERY_N and now - _last_flush < _FLUSH_EVERY_SEC:
        return
    _flush_cache()


def _flush_cache() -> None:
    """把内存缓存原子写回磁盘（临时文件 + os.replace）。

    两个坑：
    1. 直接 write_text 的话，两个请求同时落盘会互相截断，把 3MB 的缓存写坏；
    2. 内存还没加载过就落盘，会把磁盘上已有的缓存写成空字典——必须先 _load_cache()。
    """
    global _dirty, _last_flush
    if _CACHE_MEM is None:
        _load_cache()
    if not _CACHE_MEM:
        return
    cache = _CACHE_MEM
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(CACHE_FILE.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
            os.replace(tmp, CACHE_FILE)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        _dirty = 0
        _last_flush = time.time()
    except Exception as e:  # 缓存只是省调用量，写失败不影响功能
        logger.warning("embedding 缓存写入失败: %s", e)


def _flush_on_exit() -> None:
    # 只有真的攒了脏数据才落盘，避免冷进程退出时写一次空缓存
    if _dirty > 0:
        _flush_cache()


atexit.register(_flush_on_exit)


def _post(texts: list[str]) -> list[list[float]] | None:
    url, key = endpoint()
    try:
        r = requests.post(
            f"{url}/embeddings",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": settings.embedding_model, "input": texts, "encoding_format": "float"},
            timeout=20,
        )
        if r.status_code != 200:
            logger.warning("embedding 接口返回 %s: %s", r.status_code, r.text[:200])
            return None
        data = r.json().get("data") or []
        ordered = sorted(data, key=lambda d: d.get("index", 0))
        vecs = [normalize(d["embedding"]) for d in ordered]
        return vecs if len(vecs) == len(texts) else None
    except Exception as e:
        logger.warning("embedding 调用失败: %s", e)
        return None


def embed(texts: list[str], use_cache: bool = True) -> list[list[float]] | None:
    """批量向量化；命中缓存的部分不再请求。失败返回 None 由调用方降级。"""
    texts = [t for t in (texts or [])]
    if not texts:
        return []
    if not configured():
        return None

    cache = _load_cache() if use_cache else {}
    out: list[list[float] | None] = [None] * len(texts)
    todo: list[int] = []
    for i, t in enumerate(texts):
        hit = cache.get(_cache_key(t))
        if hit:
            out[i] = hit
        else:
            todo.append(i)

    for start in range(0, len(todo), BATCH):
        idxs = todo[start:start + BATCH]
        vecs = _post([texts[i] for i in idxs])
        if vecs is None and len(idxs) > 1:
            single = []
            for i in idxs:  # 批量被拒时逐条重试
                one = _post([texts[i]])
                if not one:
                    return None
                single.append(one[0])
            vecs = single
        if vecs is None:
            return None
        for i, v in zip(idxs, vecs):
            out[i] = v
            cache[_cache_key(texts[i])] = v

    if use_cache and todo:
        _save_cache(cache)
    return out


def embed_one(text: str) -> list[float] | None:
    vecs = embed([text])
    return vecs[0] if vecs else None

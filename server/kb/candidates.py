"""行程生成的候选景点池 + 真实性后置校验。

治的是这个：LLM 会编造不存在的景点、或把车站当景点写进 spots。
做法是生成前给它一份「只能从这里选」的真实名单，生成后再逐条对齐校验，
不对齐的直接换成名单里的同类景点——且整趟行程最多只发一次高德 POI 请求
（你们的 key 有 QPS 限制，实测连打 6 次就报 CUQPS_HAS_EXCEEDED_THE_LIMIT）。
"""
import logging
import re
import time

import requests

from app.config import settings
from kb.retriever import name_tokens

logger = logging.getLogger(__name__)

# 高德 POI 分类码：110100 公园广场 / 110200 风景名胜。
# 实测单用 110000 会召回纪念馆、旧址、宗祠这类不适合排进行程的条目。
ATTRACTION_TYPES = "110100|110200"
POOL_LIMIT = 18
CACHE_TTL = 1800  # 秒；同城市重复规划不该再打一次高德

_pool_cache: dict[str, tuple[float, list[dict]]] = {}
_poi_cache: dict[str, tuple[float, bool]] = {}

STATS = {
    "pool_built": 0, "amap_pois": 0, "amap_failed": 0,
    "spots_checked": 0, "spots_aligned": 0, "spots_replaced": 0, "spots_kept_unverified": 0,
    "poi_confirmed": 0, "poi_rejected": 0,
}


def is_real_attraction(name: str, city: str) -> bool:
    """池外景点的第二道判定：在高德按「风景名胜/公园」分类里能搜到，才算真实景点。

    只用于池外景点，且每次校验有调用预算（MAX_POI_CHECKS）——
    你们的 key 有 QPS 限制，模型不听话写满池外名字时不能让它打出十几次请求。
    """
    name = (name or "").strip()
    if not name or not settings.gaode_web_key:
        return False
    key = f"{city}|{name}"
    now = time.time()
    hit = _poi_cache.get(key)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        r = requests.get(
            "https://restapi.amap.com/v3/place/text",
            params={"key": settings.gaode_web_key, "city": city, "citylimit": "true",
                    "types": ATTRACTION_TYPES, "keywords": name, "offset": "1", "extensions": "base"},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        ok = str(data.get("status")) == "1" and bool(data.get("pois"))
    except Exception as e:
        logger.warning("景点真实性复核失败 %s/%s: %s", city, name, e)
        ok = False  # 查询失败时不当作已证实，交给替换逻辑，保守处理
    _poi_cache[key] = (now, ok)
    if ok:
        STATS["poi_confirmed"] += 1
    else:
        STATS["poi_rejected"] += 1
    return ok


def _clean_name(name: str) -> str:
    return re.sub(r"[\s（）()·、,，.。'’”\"“]+", "", name or "").lower()


def _corpus_spots(city: str) -> list[dict]:
    from kb import corpus

    out = []
    for d in corpus.build_docs():
        if d["kind"] != "spot" or d["city"] != city:
            continue
        m = d["meta"]
        out.append({
            "name": d["name"], "address": m.get("address") or "", "category": m.get("category") or "",
            "ticket_price": m.get("ticket_price"), "duration_min": m.get("duration_min"),
            "need_booking": m.get("need_booking"), "photo_spots": m.get("photo_spots") or [],
            "source": "corpus",
        })
    return out


def _amap_spots(city: str) -> list[dict]:
    if not settings.gaode_web_key:
        return []
    try:
        r = requests.get(
            "https://restapi.amap.com/v3/place/text",
            params={
                "key": settings.gaode_web_key, "city": city, "citylimit": "true",
                "types": ATTRACTION_TYPES, "offset": POOL_LIMIT, "page": 1,
                "sort_rule": "0", "extensions": "all",
            },
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        if str(data.get("status")) != "1":
            STATS["amap_failed"] += 1
            logger.warning("候选池高德查询失败 %s: %s", city, data.get("info"))
            return []
        out = []
        for poi in data.get("pois") or []:
            name = (poi.get("name") or "").strip()
            if not name:
                continue
            # 营业时间/评分在 biz_ext 里，不是 biz——biz 实测为 null，找错路径会误判成"高德没有该数据"
            ext = poi.get("biz_ext") or {}
            cost = ext.get("cost")
            if isinstance(cost, (list, dict)):
                cost = None
            out.append({
                "name": name, "address": (poi.get("address") or "").strip() if isinstance(poi.get("address"), str) else "",
                "category": (poi.get("type") or "").split(";")[-1],
                "location": poi.get("location") or "",
                "rating": str(ext.get("rating") or ""),
                "open_time": str(ext.get("opentime2") or ext.get("opentime") or ""),
                "cost": str(cost or ""),
                "keytag": str(poi.get("keytag") or ""),
                "tel": str(poi.get("tel") or "") if isinstance(poi.get("tel"), str) else "",
                "ticket_price": None, "duration_min": None,
                "need_booking": False, "photo_spots": [], "source": "amap",
            })
        STATS["amap_pois"] += len(out)
        return out
    except Exception as e:
        STATS["amap_failed"] += 1
        logger.warning("候选池高德请求异常 %s: %s", city, e)
        return []


def city_pool(city: str, use_cache: bool = True) -> list[dict]:
    """某城市的真实候选景点池：语料优先（字段丰富），高德补充（覆盖 9 城之外的城市）。"""
    city = (city or "").strip()
    if not city:
        return []
    now = time.time()
    if use_cache and city in _pool_cache:
        ts, pool = _pool_cache[city]
        if now - ts < CACHE_TTL:
            return pool

    pool = _corpus_spots(city)
    if len(pool) < POOL_LIMIT:
        for item in _amap_spots(city):
            if not any(_clean_name(item["name"]) == _clean_name(p["name"]) or
                       _clean_name(item["name"]) in _clean_name(p["name"]) or
                       _clean_name(p["name"]) in _clean_name(item["name"]) for p in pool):
                pool.append(item)
            if len(pool) >= POOL_LIMIT:
                break
    pool = pool[:POOL_LIMIT]
    _pool_cache[city] = (now, pool)
    STATS["pool_built"] += 1
    return pool


def find(pool: list[dict], name: str) -> dict | None:
    """把 LLM 写的景点名对齐到候选池条目。允许包含关系，因为模型常写成简称或加后缀。"""
    target = _clean_name(name)
    if not target:
        return None
    for item in pool:
        cand = _clean_name(item["name"])
        if not cand:
            continue
        if cand == target or cand in target or target in cand:
            return item
        if any(tok in target for tok in map(_clean_name, name_tokens(item["name"])) if len(tok) >= 3):
            return item
    return None


def _pick_replacement(pool: list[dict], used: set[str], category: str) -> dict | None:
    prefer = [p for p in pool if p["name"] not in used and category and category in (p.get("category") or "")]
    rest = [p for p in pool if p["name"] not in used]
    return (prefer or rest or [None])[0]


def _must_see_names(raw: str) -> set:
    parts = re.split(r"[,，、;；\s]+", raw or "")
    return {_clean_name(p) for p in parts if len(p.strip()) >= 2}


def enrich(spot: dict, item: dict) -> dict:
    """用池里的真实字段覆盖模型估的值——真实字段优先。"""
    s = dict(spot)
    s["name"] = item["name"]
    if item.get("address"):
        s["address"] = item["address"]
    if item.get("category") and not s.get("category"):
        s["category"] = item["category"]
    if item.get("ticket_price") is not None:
        s["ticket_price"] = item["ticket_price"]
    if item.get("duration_min"):
        s["duration_min"] = item["duration_min"]
    if item.get("need_booking"):
        s["need_booking"] = True
    if item.get("official_account"):
        s["official_account"] = item["official_account"]
    if item.get("photo_spots"):
        s["photo_spots"] = item["photo_spots"]
    if item.get("location"):
        s.setdefault("location", item["location"])
    return s


def verify_itinerary(content: dict, city: str, must_see: str = "", instruction: str = "",
                     max_poi_checks: int = 4) -> dict:
    """生成后逐条对齐校验。池为空时不动任何数据——宁可不校验，也不能因为检索挂了破坏行程。

    保留（不替换）的三种情况：命中候选池、用户在「必去地点」或本轮指令里点名、
    或经高德 POI 复核确认是真实景点（受 max_poi_checks 预算限制）。
    """
    pool = city_pool(city)
    result = {"pool_size": len(pool), "checked": 0, "aligned": 0, "replaced": 0,
              "unverified": 0, "poi_checked": 0, "details": [], "notices": []}
    if not pool:
        logger.info("候选池为空，跳过景点校验: %s", city)
        return result

    protected = _must_see_names(must_see)
    used: set[str] = set()
    poi_attempts = 0  # 按「尝试」而非「成功」计数，否则全查不到时预算永远不涨
    for day in (content.get("itinerary") or []):
        for spot in (day.get("spots") or []):
            hit = find(pool, spot.get("name") or "")
            if hit:
                used.add(hit["name"])

    for day in content.get("itinerary") or []:
        new_spots = []
        for spot in day.get("spots") or []:
            result["checked"] += 1
            STATS["spots_checked"] += 1
            raw_name = (spot.get("name") or "").strip()
            item = find(pool, raw_name)
            if item:
                result["aligned"] += 1
                STATS["spots_aligned"] += 1
                new_spots.append(enrich(spot, item))
                used.add(item["name"])
                continue
            named_by_user = _clean_name(raw_name) in protected or (raw_name and raw_name in (instruction or ""))
            if named_by_user:
                # 用户点名的必须保留（哪怕池里没有），但仍要复核一次真实性：
                # 实测用户说"加个杭州星空梦幻乐园"这种编造地名时，之前会被静默照单全收。
                confirmed: bool | None = None
                if poi_attempts < max_poi_checks:
                    poi_attempts += 1
                    confirmed = is_real_attraction(raw_name, city)
                result["unverified"] += 1
                STATS["spots_kept_unverified"] += 1
                detail = {"kept": raw_name, "reason": "用户点名"}
                if confirmed is False:
                    detail["notice"] = "未在高德景点库收录，请确认名称"
                    result["notices"].append({"name": raw_name, "notice": detail["notice"]})
                result["details"].append(detail)
                new_spots.append(spot)
                continue
            if poi_attempts < max_poi_checks:
                poi_attempts += 1
                if is_real_attraction(raw_name, city):
                    result["poi_checked"] += 1
                    result["unverified"] += 1
                    STATS["spots_kept_unverified"] += 1
                    result["details"].append({"kept": raw_name, "reason": "池外但POI证实存在"})
                    new_spots.append(spot)
                    continue
            repl = _pick_replacement(pool, used, spot.get("category") or "")
            if repl:
                result["replaced"] += 1
                STATS["spots_replaced"] += 1
                result["details"].append({"from": raw_name, "to": repl["name"], "reason": "不在候选池"})
                new_spots.append(enrich(spot, repl))
                used.add(repl["name"])
            else:
                result["unverified"] += 1
                STATS["spots_kept_unverified"] += 1
                result["details"].append({"kept": raw_name, "reason": "池内无可替换项"})
                new_spots.append(spot)
        day["spots"] = new_spots

    logger.info("景点校验 %s: 池%d 对齐%d 替换%d 保留%d（POI复核%d）", city, result["pool_size"],
                result["aligned"], result["replaced"], result["unverified"], result["poi_checked"])
    return result


def format_pool(pool: list[dict], limit: int = POOL_LIMIT) -> str:
    """压成 prompt 里的一段名单，控制 token 体积。"""
    lines = []
    for i, p in enumerate(pool[:limit], 1):
        extras = []
        if p.get("category"):
            extras.append(str(p["category"]))
        if p.get("address"):
            extras.append(p["address"][:20])
        if p.get("ticket_price") is not None:
            extras.append("免费" if not p["ticket_price"] else f"门票约{p['ticket_price']}元")
        if p.get("need_booking"):
            extras.append("需预约")
        lines.append(f"{i}. {p['name']}" + (f"（{'，'.join(extras)}）" if extras else ""))
    return "\n".join(lines)

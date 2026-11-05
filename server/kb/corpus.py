"""语料层：把 city_spots.json 拍平成可检索文档。

一条文档 = 一个能独立回答的事实（单个景点 / 单家餐厅），不做跨景点合并——
合并后命中一段就得把整包塞进 prompt，既浪费上下文也没法标注引用来源。
"""
import json
from pathlib import Path

CORPUS_FILE = Path(__file__).resolve().parent / "corpus" / "city_spots.json"


def _truthy(v) -> bool:
    """兼容历史语料里 true/是的/1/False 混着写的情况。"""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "y", "是", "需要", "要"}
    return False


def load_spots(path=None) -> dict:
    return json.loads(Path(path or CORPUS_FILE).read_text(encoding="utf-8"))


def _spot_text(city: str, s: dict, route_types: list) -> str:
    parts = [f"{city}·{s.get('name', '').strip()}"]
    if s.get("category"):
        parts.append(str(s["category"]))
    if s.get("description"):
        parts.append(str(s["description"]).strip())
    price = s.get("ticket_price")
    if price is not None:
        parts.append("门票免费" if not price else f"门票约{price}元")
    if s.get("duration_min"):
        parts.append(f"建议游玩{ s['duration_min']}分钟")
    if _truthy(s.get("need_booking")):
        parts.append("需要提前预约")
    if s.get("official_account"):
        parts.append(f"预约入口：{s['official_account']}")
    if s.get("address"):
        parts.append(f"地址：{s['address']}")
    photos = s.get("photo_spots") or []
    if photos:
        names = [p.get("name") if isinstance(p, dict) else p for p in photos]
        parts.append("打卡机位：" + "、".join(str(n) for n in names if n))
    parts.append("适合" + "/".join(route_types) + "路线")
    return "；".join(p for p in parts if p)


def _meal_text(city: str, m: dict) -> str:
    parts = [f"{city}·{m.get('name', '').strip()}"]
    if m.get("type"):
        parts.append(f"适合{m['type']}")
    if m.get("specialty"):
        parts.append(f"招牌：{m['specialty']}")
    if m.get("avg_price"):
        parts.append(f"人均约{m['avg_price']}元")
    if m.get("address"):
        parts.append(f"地址：{m['address']}")
    return "；".join(p for p in parts if p)


def poi_doc(item: dict, city: str) -> dict:
    """把一条高德 POI 转成与语料同构的检索文档。

    POI 没有 description / 机位 / 票价，但有真实地址、坐标、评分、分类——
    它回答的是「这个景点确实存在、在哪、什么类型」，语料回答的是「怎么玩」。
    """
    city = city or (item.get("city") or "")
    name = (item.get("name") or "").strip()
    parts = [f"{city}·{name}"]
    if item.get("keytag"):
        parts.append(str(item["keytag"]))
    elif item.get("category"):
        parts.append(str(item["category"]))
    if item.get("address"):
        parts.append(f"地址：{item['address']}")
    if item.get("rating"):
        parts.append(f"评分{item['rating']}")
    if item.get("open_time"):
        parts.append(f"开放时间：{item['open_time']}")
    if item.get("tel"):
        parts.append(f"咨询电话：{item['tel']}")
    meta = {
        "city": city, "name": name, "category": item.get("category"),
        "address": item.get("address"), "location": item.get("location"),
        "rating": item.get("rating"), "open_time": item.get("open_time"),
        "keytag": item.get("keytag"), "tel": item.get("tel"),
        "ticket_price": item.get("ticket_price"), "duration_min": item.get("duration_min"),
        "need_booking": bool(item.get("need_booking")), "photo_spots": item.get("photo_spots") or [],
        "source": item.get("source") or "amap",
    }
    return {"id": f"{city}|spot|{name}", "kind": "spot", "city": city, "name": name,
            "text": "；".join(p for p in parts if p), "meta": meta}


def merge_docs(*groups: list[dict]) -> list[dict]:
    """按 id 合并多组文档，先到先得——语料在前，POI 只补语料没有的景点。"""
    out: list[dict] = []
    seen: set[str] = set()
    for group in groups:
        for d in group:
            if d["id"] in seen:
                continue
            seen.add(d["id"])
            out.append(d)
    return out


def build_docs(spots: dict | None = None) -> list[dict]:
    """返回文档列表；同一景点在大众/小众路线里重复出现时合并成一条。"""
    data = spots if spots is not None else load_spots()
    docs: list[dict] = []
    seen: dict[str, int] = {}

    for city, repo in (data or {}).items():
        if not isinstance(repo, dict):
            continue
        for route_type in ("popular", "niche"):
            for day in repo.get(route_type) or []:
                if not isinstance(day, list):
                    continue
                for s in day:
                    if not isinstance(s, dict) or not s.get("name"):
                        continue
                    doc_id = f"{city}|spot|{s['name']}"
                    if doc_id in seen:
                        merged = docs[seen[doc_id]]["meta"]["route_types"]
                        if route_type not in merged:
                            merged.append(route_type)
                        continue
                    meta = {
                        "city": city,
                        "name": s["name"],
                        "category": s.get("category"),
                        "ticket_price": s.get("ticket_price"),
                        "duration_min": s.get("duration_min"),
                        "need_booking": _truthy(s.get("need_booking")),
                        "official_account": s.get("official_account"),
                        "address": s.get("address"),
                        "photo_spots": s.get("photo_spots") or [],
                        "route_types": [route_type],
                    }
                    seen[doc_id] = len(docs)
                    docs.append({"id": doc_id, "kind": "spot", "city": city,
                                 "name": s["name"], "text": _spot_text(city, s, [route_type]), "meta": meta})

        for m in repo.get("meals") or []:
            if not isinstance(m, dict) or not m.get("name"):
                continue
            doc_id = f"{city}|meal|{m['name']}"
            if doc_id in seen:
                continue
            meta = {"city": city, "name": m["name"], "type": m.get("type"),
                    "avg_price": m.get("avg_price"), "specialty": m.get("specialty"),
                    "address": m.get("address")}
            seen[doc_id] = len(docs)
            docs.append({"id": doc_id, "kind": "meal", "city": city,
                         "name": m["name"], "text": _meal_text(city, m), "meta": meta})

    return docs

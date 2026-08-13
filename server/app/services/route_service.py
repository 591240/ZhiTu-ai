# app/services/route_service.py —— 真实市内公共交通路线规划（高德地图）
# 根据起点/终点地名 + 城市，调用高德「公交路径规划」API，返回可读的线路/车次/步行段。

import logging
from urllib.parse import quote

import requests

from app.config import settings
from app.services import image_service

logger = logging.getLogger(__name__)

# 本地内存缓存：同一进程内避免重复请求
_route_cache: dict[str, dict | None] = {}


def _cache_key(origin: str, dest: str, city: str, mode: str) -> str:
    return f"{city}|{mode}|{origin}->{dest}"


def _safe_int(v, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def _location_of(name: str, city: str) -> str | None:
    """通过 image_service 的 POI 查询拿到地名经纬度（格式：lng,lat）。"""
    info = image_service.get_spot_info(name, city)
    return info.get("location") if info else None


def _human_detail(segments: list) -> str:
    """把 segments 拼成一句话 readable 方案。"""
    parts = []
    for seg in segments:
        if seg.get("type") == "walking":
            parts.append(f"步行{seg.get('distance', 0)}米约{seg.get('duration_min', 0)}分钟")
        elif seg.get("type") in ("bus", "subway"):
            parts.append(
                f"乘坐{seg.get('line', '公交')}（{seg.get('from_stop', '起点')}→{seg.get('to_stop', '终点')}，"
                f"{seg.get('stations', 0)}站）"
            )
    return "，".join(parts) if parts else "公共交通"


def get_transit_route(origin_name: str, dest_name: str, city: str, mode: str = "公交") -> dict | None:
    """
    查询两地之间的公共交通方案。
    返回：{
        "mode": "公交",
        "duration_min": int,
        "cost": int,
        "detail": str,
        "segments": [
            {"type":"walking", "distance":300, "duration_min":5, "instruction":"步行300米"},
            {"type":"bus|subway", "line":"9路", "from_stop":"A站", "to_stop":"B站", "stations":4, "duration_min":15}
        ]
    }
    """
    if not settings.gaode_web_key:
        return None

    mode = (mode or "公交").replace("公共交通", "公交").replace("地铁", "公交")
    cache_key = _cache_key(origin_name, dest_name, city, mode)
    if cache_key in _route_cache:
        return _route_cache[cache_key]

    origin_loc = _location_of(origin_name, city)
    dest_loc = _location_of(dest_name, city)
    if not origin_loc or not dest_loc:
        logger.warning("无法获取起点/终点坐标: %s / %s", origin_name, dest_name)
        _route_cache[cache_key] = None
        return None

    try:
        url = (
            "https://restapi.amap.com/v3/direction/transit/integrated"
            f"?key={settings.gaode_web_key}"
            f"&origin={origin_loc}"
            f"&destination={dest_loc}"
            f"&city1={quote(city)}"
            f"&city2={quote(city)}"
            f"&extensions=all"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if str(data.get("status")) != "1":
            logger.warning("高德公交路径规划失败: %s", data.get("info"))
            _route_cache[cache_key] = None
            return None

        transits = data.get("route", {}).get("transits") or []
        if not transits:
            _route_cache[cache_key] = None
            return None

        best = transits[0]
        cost_info = best.get("cost", {}) or {}
        if isinstance(cost_info, str):
            cost_info = {}
        total_duration_sec = _safe_int(cost_info.get("duration") if isinstance(cost_info, dict) else 0, 0)
        total_cost_yuan = _safe_int(cost_info.get("trans_fee") if isinstance(cost_info, dict) else 0, 0)

        segments = []
        for seg in best.get("segments") or []:
            # 步行段
            walking = seg.get("walking")
            if walking:
                steps = walking.get("steps") or []
                instruction = steps[0].get("instruction") if steps else f"步行{walking.get('distance', 0)}米"
                segments.append({
                    "type": "walking",
                    "distance": _safe_int(walking.get("distance"), 0),
                    "duration_min": _safe_int(walking.get("duration"), 0) // 60,
                    "instruction": instruction or f"步行{walking.get('distance', 0)}米",
                })

            # 公共交通段
            bus_info = seg.get("bus")
            if bus_info:
                lines = bus_info.get("buslines") or []
                if lines:
                    line = lines[0]
                    line_name = line.get("name", "公交").split("(")[0].strip()
                    line_type = "subway" if (line.get("type") == "地铁" or "地铁" in line_name or line_name.endswith("号线")) else "bus"
                    dep = line.get("departure_stop", {})
                    arr = line.get("arrival_stop", {})
                    segments.append({
                        "type": line_type,
                        "line": line_name,
                        "from_stop": dep.get("name", ""),
                        "to_stop": arr.get("name", ""),
                        "stations": _safe_int(line.get("via_num"), 0),
                        "duration_min": _safe_int(line.get("duration"), 0) // 60,
                        "distance": _safe_int(line.get("distance"), 0),
                    })

        result = {
            "mode": mode,
            "duration_min": max(1, total_duration_sec // 60),
            "cost": total_cost_yuan,
            "detail": _human_detail(segments),
            "segments": segments,
        }
        _route_cache[cache_key] = result
        return result
    except Exception:
        logger.exception("查询公交路线失败: %s -> %s", origin_name, dest_name)
        _route_cache[cache_key] = None
        return None

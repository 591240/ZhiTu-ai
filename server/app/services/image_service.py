# app/services/image_service.py —— 景点/城市封面图获取
# 当前使用高德地图 POI 搜索返回的真实照片（需 GAODE_WEB_KEY）。
# 若 key 未配置或接口失败，返回 None，由调用方自行兜底。

import hashlib
import logging
from urllib.parse import quote

import requests

from app.config import settings

logger = logging.getLogger(__name__)

# 本地内存缓存：避免同一进程内重复请求高德接口
# value 为 dict {"image": str|None, "location": "lng,lat"|None}
_spot_cache: dict[str, dict | None] = {}


def _cache_key(name: str, city: str = "") -> str:
    return hashlib.md5(f"{city}|{name}".encode("utf-8")).hexdigest()


def _pick_image(pois: list) -> str | None:
    """从 POI 列表里挑一张可用的真实图片 URL（统一返回 https，适配小程序真机）。"""
    if not pois:
        return None
    photos = pois[0].get("photos") or []
    candidates = []
    for photo in photos:
        img_url = photo.get("url")
        if not img_url or not str(img_url).startswith("http"):
            continue
        # 微信真机默认禁止 http 图片，统一升级为 https
        img_url = str(img_url).replace("http://", "https://", 1)
        if "store.is.autonavi.com" in img_url:
            candidates.insert(0, img_url)
        else:
            candidates.append(img_url)
    for img_url in candidates:
        try:
            head = requests.head(img_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if head.status_code == 200:
                return img_url
        except Exception:
            continue
    return candidates[0] if candidates else None


def _parse_location(poi: dict) -> str | None:
    """从 POI 中提取经纬度（高德返回 'lng,lat'）。"""
    loc = poi.get("location")
    if loc and isinstance(loc, str) and "," in loc:
        parts = loc.split(",")
        if len(parts) == 2:
            try:
                float(parts[0])
                float(parts[1])
                return loc
            except Exception:
                pass
    return None


def get_spot_info(name: str, city: str = "") -> dict | None:
    """
    根据景点/地名和城市，从高德 POI 搜索获取：
      - image: 真实封面图 URL（可能为 None）
      - location: 经纬度字符串 "lng,lat"（可能为 None）
    结果会被缓存。
    """
    if not settings.gaode_web_key:
        return None
    key = _cache_key(name, city)
    if key in _spot_cache:
        return _spot_cache[key]

    try:
        url = (
            "https://restapi.amap.com/v3/place/text"
            f"?key={settings.gaode_web_key}"
            f"&keywords={quote(name)}"
            f"&city={quote(city or '')}"
            f"&offset=1"
            f"&extensions=all"
        )
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        data = r.json()
        if str(data.get("status")) != "1":
            logger.warning("高德 POI 搜索失败: %s", data.get("info"))
            _spot_cache[key] = None
            return None
        pois = data.get("pois") or []
        if not pois:
            _spot_cache[key] = None
            return None
        result = {
            "image": _pick_image(pois),
            "location": _parse_location(pois[0]),
        }
        _spot_cache[key] = result
        return result
    except Exception:
        logger.exception("获取景点信息失败: %s / %s", city, name)
        _spot_cache[key] = None
        return None


def get_spot_image(name: str, city: str = "") -> str | None:
    """根据景点名称和城市，从高德 POI 搜索获取一张真实封面图 URL（同步请求）。"""
    info = get_spot_info(name, city)
    return info.get("image") if info else None


def get_spot_location(name: str, city: str = "") -> str | None:
    """根据景点名称和城市，从高德 POI 搜索获取经纬度 'lng,lat'。"""
    info = get_spot_info(name, city)
    return info.get("location") if info else None

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
_image_cache: dict[str, str | None] = {}


def _cache_key(name: str, city: str = "") -> str:
    return hashlib.md5(f"{city}|{name}".encode("utf-8")).hexdigest()


def get_spot_image(name: str, city: str = "") -> str | None:
    """根据景点名称和城市，从高德 POI 搜索获取一张真实封面图 URL（同步请求）。"""
    if not settings.gaode_web_key:
        return None
    key = _cache_key(name, city)
    if key in _image_cache:
        return _image_cache[key]

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
            _image_cache[key] = None
            return None
        pois = data.get("pois") or []
        if not pois:
            _image_cache[key] = None
            return None
        photos = pois[0].get("photos") or []
        # 优先选 store.is.autonavi.com 的官方图片（更稳定）；
        # 再按返回顺序逐个验证可访问性，避免 404 失效链接。
        candidates = []
        for photo in photos:
            img_url = photo.get("url")
            if not img_url or not str(img_url).startswith("http"):
                continue
            if "store.is.autonavi.com" in img_url:
                candidates.insert(0, img_url)
            else:
                candidates.append(img_url)
        for img_url in candidates:
            try:
                head = requests.head(img_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                if head.status_code == 200:
                    _image_cache[key] = img_url
                    return img_url
            except Exception:
                continue
        # 全部验证失败时，返回第一张候选（让前端自己处理加载失败）
        if candidates:
            _image_cache[key] = candidates[0]
            return candidates[0]
        _image_cache[key] = None
        return None
    except Exception:
        logger.exception("获取景点图片失败: %s / %s", city, name)
        _image_cache[key] = None
        return None

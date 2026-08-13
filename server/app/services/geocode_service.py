"""地理编码服务：地名/车站/景点 → 经纬度。

优先级：腾讯位置服务 WebService（tencent_lbs_key）→ 高德 MCP（gaode_mcp_url）→
高德 REST（gaode_web_key）→ 内置坐标表 → None。
- 腾讯/高德均返回 gcj-02 坐标，与 wx.getLocation(type=gcj02) / wx.openLocation 同一坐标系，零偏移。
- 内置表保证开发阶段零依赖也能精准定位常见高铁站与热门景点。
"""
import json
import logging
import re
import urllib.parse

import httpx

from app.ai.mcp_client import call_mcp_tool
from app.config import settings

logger = logging.getLogger(__name__)

# 内置热门车站/城市坐标（lat, lng）。开发期零依赖可用；MCP 接入后覆盖更全。
STATION_COORDS = {
    "北京": (39.9042, 116.4074), "北京南站": (39.8657, 116.3786), "北京南": (39.8657, 116.3786),
    "北京西站": (39.8949, 116.3220), "北京站": (39.9027, 116.4271),
    "上海": (31.2304, 121.4737), "上海虹桥站": (31.1942, 121.3199), "上海虹桥": (31.1942, 121.3199),
    "上海站": (31.2492, 121.4570),
    "杭州": (30.2741, 120.1551), "杭州东站": (30.2741, 120.2120), "杭州东": (30.2741, 120.2120),
    "杭州站": (30.2520, 120.1650),
    "南京": (32.0603, 118.7969), "南京南站": (31.9893, 118.7996), "南京南": (31.9893, 118.7996),
    "成都": (30.5728, 104.0668), "成都东站": (30.6306, 104.1414), "成都东": (30.6306, 104.1414),
    "广州": (23.1291, 113.2644), "广州南站": (22.9900, 113.2730), "广州南": (22.9900, 113.2730),
    "深圳": (22.5431, 114.0579), "深圳北站": (22.6090, 114.3250), "深圳北": (22.6090, 114.3250),
    "武汉": (30.5928, 114.3055), "汉口站": (30.6030, 114.2920), "汉口": (30.6030, 114.2920),
    "西安": (34.3416, 108.9398), "西安北站": (34.3844, 108.9450), "西安北": (34.3844, 108.9450),
    "长沙": (28.2282, 112.9388), "长沙南站": (28.1570, 113.0210), "长沙南": (28.1570, 113.0210),
    "重庆": (29.5630, 106.5516), "重庆北站": (29.6110, 106.5530), "重庆北": (29.6110, 106.5530),
    "厦门": (24.4798, 118.0894), "厦门北站": (24.6220, 118.0870), "厦门北": (24.6220, 118.0870),
    "苏州": (31.2989, 120.5853), "苏州站": (31.3170, 120.6160),
    "青岛": (36.0671, 120.3826), "青岛站": (36.0660, 120.3200),
    "天津": (39.3434, 117.3616), "天津站": (39.1430, 117.2080),
    "济南": (36.6512, 117.1201), "济南西站": (36.6500, 116.8900),
    "郑州": (34.7466, 113.6254), "郑州东站": (34.7580, 113.7840), "郑州东": (34.7580, 113.7840),
    "昆明": (24.8801, 102.8329), "昆明南站": (24.8840, 102.8540),
    "合肥": (31.8206, 117.2272), "合肥南站": (31.8000, 117.2800),
    "福州": (26.0745, 119.2965), "福州站": (26.0830, 119.3100),
    "南昌": (28.6829, 115.8579), "南昌西站": (28.6400, 115.8200),
    "太原": (37.8706, 112.5489), "太原南站": (37.7800, 112.5700),
    "石家庄": (38.0428, 114.5149), "石家庄站": (38.0300, 114.4900),
    "宁波": (29.8683, 121.5440), "宁波站": (29.8700, 121.5400),
    "无锡": (31.4912, 120.3119), "无锡站": (31.5800, 120.3100),
    "常州": (31.8110, 119.9740), "常州站": (31.8100, 119.9700),
    "温州": (27.9938, 120.6994), "温州南站": (27.9600, 120.7000),
    "桂林": (25.2736, 110.2900), "桂林北站": (25.3300, 110.3000),
    "丽江": (26.8721, 100.2299), "大理": (25.6065, 100.2676),
    "三亚": (18.2528, 109.5119), "海口": (20.0440, 110.1999),
}

# 内置热门景点坐标（开发期零依赖即可算距/导航；接腾讯位置服务 key 后覆盖更全面）。
SCENIC_COORDS = {
    # 杭州
    "西湖": (30.2592, 120.1490), "灵隐寺": (30.2410, 120.0990), "西溪湿地": (30.2700, 120.0700),
    "河坊街": (30.2430, 120.1700), "九溪烟树": (30.2100, 120.1200), "良渚古城遗址": (30.4000, 119.9800),
    "龙井村": (30.2100, 120.1300), "断桥": (30.2595, 120.1485), "苏堤": (30.2450, 120.1450),
    "雷峰塔": (30.2310, 120.1480), "千岛湖": (29.6000, 119.0400),
    # 成都
    "宽窄巷子": (30.6690, 104.0560), "锦里": (30.6420, 104.0450), "武侯祠": (30.6420, 104.0450),
    "大熊猫繁育研究基地": (30.7330, 104.1460), "春熙路": (30.6570, 104.0810), "玉林路小酒馆": (30.6320, 104.0930),
    "东郊记忆": (30.6700, 104.1100), "杜甫草堂": (30.6590, 104.0280), "金沙遗址": (30.6820, 104.0100),
    "都江堰": (31.0040, 103.6180), "青城山": (30.9000, 103.5660),
}

# 内置餐饮店坐标（开发期零依赖即可算距/导航；接腾讯位置服务 key 后覆盖更全面）。
RESTAURANT_COORDS = {
    # 杭州
    "外婆家": (30.2741, 120.1551), "楼外楼": (30.2590, 120.1450), "知味观": (30.2580, 120.1650),
    # 成都
    "小龙坎火锅": (30.6570, 104.0810), "陈麻婆豆腐": (30.6590, 104.0280), "甜水面": (30.6570, 104.0810),
}


class GeocodeService:
    async def geocode(self, name: str, city: str = "") -> dict | None:
        name = (name or "").strip()
        city = (city or "").strip()
        if not name:
            return None

        # 1) 腾讯位置服务（gcj-02，与微信地图坐标系一致，零偏移；带城市更准）
        key = settings.tencent_lbs_key
        if key:
            try:
                loc = await self._geocode_tencent(name, key, city)
                if loc:
                    return loc
                logger.warning("腾讯位置服务未解析到坐标：%s", name)
            except Exception as e:
                logger.warning("腾讯位置服务 geocode 失败：%s", e)

        # 2) 精确内置表：常见车站/城市/景点/餐厅，坐标已知正确，优先于无城市的外部 API
        exact = self._exact_builtin_lookup(name)
        if exact:
            return exact

        # 3) 高德 MCP（若配置）
        url = settings.gaode_mcp_url
        if url:
            try:
                text = await call_mcp_tool(url, settings.gaode_geocode_tool, {"address": name, "city": city})
                loc = self._parse_gaode(text, name)
                if loc:
                    return loc
                logger.warning("高德 MCP geocode 未解析到坐标，降级高德 REST：%s", name)
            except Exception as e:
                logger.warning("高德 MCP geocode 失败，降级高德 REST：%s", e)

        # 4) 高德 REST（带城市可消除「西湖」匹配到台湾等歧义）
        gd_key = settings.gaode_web_key
        if gd_key:
            try:
                loc = await self._geocode_gaode_rest(name, gd_key, city)
                if loc:
                    return loc
                logger.warning("高德 REST geocode 未解析到坐标，降级内置表：%s", name)
            except Exception as e:
                logger.warning("高德 REST geocode 失败，降级内置表：%s", e)

        # 5) 内置表模糊匹配：去"站"后缀 / 子串
        coords = self._table_lookup(name)
        if coords:
            return {"lat": coords[0], "lng": coords[1], "name": name, "address": name, "source": "builtin"}
        sc = self._scenic_lookup(name)
        if sc:
            return {"lat": sc[0], "lng": sc[1], "name": name, "address": name, "source": "builtin-scenic"}
        rc = self._restaurant_lookup(name)
        if rc:
            return {"lat": rc[0], "lng": rc[1], "name": name, "address": name, "source": "builtin-restaurant"}
        return None

    async def geocode_batch(self, names: list[str], city: str = "") -> list[dict]:
        """批量地理编码，返回与输入顺序一致的结果列表（查不到为 None）。"""
        out = []
        for n in names:
            out.append(await self.geocode(n, city))
        return out

    async def reverse_geocode(self, lat: float, lng: float) -> dict | None:
        """经纬度 → 城市名（gcj-02 坐标系）。优先腾讯位置服务，降级高德 REST。"""
        # 1) 腾讯位置服务逆地址解析
        key = settings.tencent_lbs_key
        if key:
            try:
                city = await self._reverse_geocode_tencent(lat, lng, key)
                if city:
                    return {"city": city, "source": "tencent-lbs"}
            except Exception as e:
                logger.warning("腾讯位置服务 reverse-geocode 失败：%s", e)

        # 2) 高德 REST 逆地理编码
        gd_key = settings.gaode_web_key
        if gd_key:
            try:
                city = await self._reverse_geocode_gaode_rest(lat, lng, gd_key)
                if city:
                    return {"city": city, "source": "gaode-rest"}
            except Exception as e:
                logger.warning("高德 REST reverse-geocode 失败：%s", e)

        return None

    @staticmethod
    def normalize_city(raw: str | None) -> str | None:
        """把逆地理编码返回的行政区划名统一成 mockCities 中的城市名（无'市'后缀）。"""
        if not raw:
            return None
        raw = raw.strip()
        if not raw:
            return None
        # 直辖市
        for direct in ("北京", "上海", "天津", "重庆"):
            if direct in raw:
                return direct
        # 去掉常见后缀：市、地区、自治州、盟
        cleaned = raw.replace("市", "").replace("地区", "").replace("自治州", "").replace("盟", "")
        cleaned = cleaned.strip()
        return cleaned or None

    @staticmethod
    async def _reverse_geocode_tencent(lat: float, lng: float, key: str) -> str | None:
        params = {"location": f"{lat},{lng}", "key": key, "get_poi": 0}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://apis.map.qq.com/ws/geocoder/v1/",
                params=params, timeout=10,
            )
        obj = r.json()
        if obj.get("status") != 0:
            logger.warning("腾讯位置服务 reverse-geocode 返回异常：%s", obj.get("message"))
            return None
        ac = (obj.get("result") or {}).get("address_component") or {}
        city = ac.get("city") or ac.get("province")
        return GeocodeService.normalize_city(city)

    @staticmethod
    async def _reverse_geocode_gaode_rest(lat: float, lng: float, key: str) -> str | None:
        """高德逆地理编码：location=经度,纬度。"""
        params = {"key": key, "location": f"{lng},{lat}", "extensions": "base", "output": "JSON"}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://restapi.amap.com/v3/geocode/regeo",
                params=params, timeout=10,
            )
        obj = r.json()
        if str(obj.get("status")) != "1":
            logger.warning("高德 REST reverse-geocode 返回异常：status=%s info=%s", obj.get("status"), obj.get("info"))
            return None
        ac = (obj.get("regeocode") or {}).get("addressComponent") or {}
        city = ac.get("city") or ac.get("province")
        return GeocodeService.normalize_city(city)

    @staticmethod
    async def _geocode_tencent(name: str, key: str, city: str = "") -> dict | None:
        params = {"address": name, "key": key}
        if city:
            params["region"] = city
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://apis.map.qq.com/ws/geocoder/v1/",
                params=params, timeout=10,
            )
        try:
            obj = r.json()
        except Exception:
            return None
        if obj.get("status") != 0:
            logger.warning("腾讯位置服务返回异常：%s", obj.get("message"))
            return None
        loc = (obj.get("result") or {}).get("location") or {}
        lat = loc.get("lat")
        lng = loc.get("lng")
        if lat is None or lng is None:
            return None
        address = (obj.get("result") or {}).get("address") or name
        return {"lat": float(lat), "lng": float(lng), "name": name, "address": address, "source": "tencent-lbs"}

    @staticmethod
    async def _geocode_gaode_rest(name: str, key: str, city: str = "") -> dict | None:
        """高德地图地理编码 REST API（https://lbs.amap.com/api/webservice/guide/api/georegeo）。"""
        params = {"key": key, "address": name, "output": "JSON"}
        if city:
            params["city"] = city
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://restapi.amap.com/v3/geocode/geo",
                params=params, timeout=10,
            )
        try:
            obj = r.json()
        except Exception:
            return None
        status = obj.get("status")
        info = obj.get("info", "")
        if str(status) != "1":
            logger.warning("高德 REST geocode 返回异常：status=%s info=%s", status, info)
            return None
        geocodes = obj.get("geocodes") or []
        if not geocodes:
            return None
        item = geocodes[0]
        loc = item.get("location", "")
        if not loc or "," not in loc:
            return None
        try:
            lng, lat = loc.split(",")
            lat, lng = float(lat), float(lng)
        except Exception:
            return None
        address = item.get("formatted_address") or name
        return {"lat": lat, "lng": lng, "name": name, "address": address, "source": "gaode-rest"}

    @staticmethod
    def _table_lookup(name: str):
        if name in STATION_COORDS:
            return STATION_COORDS[name]
        key = name.rstrip("站")
        if key in STATION_COORDS:
            return STATION_COORDS[key]
        for k, v in STATION_COORDS.items():
            if k in name or name in k:
                return v
        return None

    @staticmethod
    def _scenic_lookup(name: str):
        if name in SCENIC_COORDS:
            return SCENIC_COORDS[name]
        for k, v in SCENIC_COORDS.items():
            if k in name or name in k:
                return v
        return None

    @staticmethod
    def _restaurant_lookup(name: str):
        if name in RESTAURANT_COORDS:
            return RESTAURANT_COORDS[name]
        for k, v in RESTAURANT_COORDS.items():
            if k in name or name in k:
                return v
        return None

    @staticmethod
    def _exact_builtin_lookup(name: str):
        """精确匹配内置坐标表（避免「西湖」被无城市的外部 API 解析到台湾等歧义）。"""
        if name in STATION_COORDS:
            lat, lng = STATION_COORDS[name]
            return {"lat": lat, "lng": lng, "name": name, "address": name, "source": "builtin"}
        if name in SCENIC_COORDS:
            lat, lng = SCENIC_COORDS[name]
            return {"lat": lat, "lng": lng, "name": name, "address": name, "source": "builtin-scenic"}
        if name in RESTAURANT_COORDS:
            lat, lng = RESTAURANT_COORDS[name]
            return {"lat": lat, "lng": lng, "name": name, "address": name, "source": "builtin-restaurant"}
        return None

    @staticmethod
    def _parse_gaode(text: str | None, name: str):
        """解析高德 MCP 返回，兼容多种结构：
        - 官方 maps_geo：{"geocodes":[{"location":"116.48,39.99",...}]}
        - 通用：{"location":{"lng":..,"lat":..}} 或 {"location":"lng,lat"}
        - 纯文本退化：正则抓 "经度,纬度"
        高德返回坐标为 gcj-02，与腾讯/微信地图同一坐标系，零偏移。
        """
        if not text:
            return None
        try:
            obj = json.loads(text)
        except Exception:
            obj = None
        if obj:
            loc = GeocodeService._extract_loc(obj)
            if loc:
                lat, lng = loc
                return {"lat": lat, "lng": lng, "name": name, "address": name, "source": "gaode-mcp"}
        m = re.search(r"(\d{2,3}\.\d{3,7})\s*,\s*(\d{2,3}\.\d{3,7})", text)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            # 中国经纬度范围：经度约 73~135，纬度约 3~54；据此判断 a/b 谁是经度
            lng, lat = (a, b) if a >= b else (b, a)
            return {"lat": lat, "lng": lng, "name": name, "address": name, "source": "gaode-mcp"}
        return None

    @staticmethod
    def _extract_loc(obj) -> tuple | None:
        """从高德 MCP 多种返回结构中提取 (lat, lng)。"""
        direct = obj.get("location") or (obj.get("data") or {}).get("location")
        r = GeocodeService._parse_loc_field(direct)
        if r:
            return r
        for key in ("geocodes", "pois", "results", "tips"):
            arr = obj.get(key) or (obj.get("data") or {}).get(key)
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, dict):
                        lr = GeocodeService._parse_loc_field(item.get("location"))
                        if lr:
                            return lr
        return None

    @staticmethod
    def _parse_loc_field(loc) -> tuple | None:
        if isinstance(loc, dict):
            lng = loc.get("lng") or loc.get("lon") or loc.get("longitude")
            lat = loc.get("lat") or loc.get("latitude")
            if lng is not None and lat is not None:
                return (float(lat), float(lng))
        if isinstance(loc, str) and "," in loc:
            parts = loc.split(",")
            if len(parts) >= 2:
                try:
                    a, b = float(parts[0].strip()), float(parts[1].strip())
                except Exception:
                    return None
                # 高德/腾讯均返回 "经度,纬度"
                return (b, a) if a >= b else (a, b)
        return None


geocode_service = GeocodeService()

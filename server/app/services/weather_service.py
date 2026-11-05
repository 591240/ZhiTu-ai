"""真实天气服务（高德 weatherInfo，extensions=all 取 4 天预报）。

为什么天气要由服务端覆盖而不是交给模型写：它是事实字段，模型没有事实来源时
会直接编造（旧 prompt 里甚至写死过「今日晴」作为示例）。这里的原则和检索层一致——
拿不到真数据就留空并说明，绝不猜。

注意：city 参数实测可直接用中文城市名，不需要 adcode；但预报只有 4 天，
出发日期超出范围时必须如实说明，不能拿今天的天气冒充下周三。
"""
import logging
import time
from datetime import date, datetime, timedelta

import requests

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_TTL = 1800  # 同城市重复规划不该再打高德（key 有 QPS 限制）
FORECAST_DAYS = 4

_cache: dict[str, tuple[float, dict]] = {}

STATS = {"calls": 0, "ok": 0, "failed": 0, "days_out_of_range": 0}


def _parse_day(raw: str) -> date | None:
    try:
        return datetime.strptime((raw or "").strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def get_forecast(city: str) -> dict[str, dict]:
    """返回 {日期字符串: {day_weather, night_weather, day_temp, night_temp, wind, ...}}。

    失败（无 key / 网络异常 / 非 1 状态）返回空字典，由调用方降级。
    """
    city = (city or "").strip()
    if not city or not settings.gaode_web_key:
        return {}
    now = time.time()
    hit = _cache.get(city)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]

    data: dict[str, dict] = {}
    try:
        STATS["calls"] += 1
        r = requests.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params={"key": settings.gaode_web_key, "city": city, "extensions": "all"},
            timeout=6,
        )
        r.raise_for_status()
        body = r.json()
        if str(body.get("status")) != "1":
            STATS["failed"] += 1
            logger.warning("天气接口返回异常 %s: %s", city, body.get("info"))
        else:
            forecasts = body.get("forecasts") or []
            for c in (forecasts[0].get("casts") or []) if forecasts else []:
                d = _parse_day(c.get("date"))
                if not d:
                    continue
                data[c["date"]] = {
                    "day_weather": c.get("dayweather") or "",
                    "night_weather": c.get("nightweather") or "",
                    "day_temp": str(c.get("daytemp") or ""),
                    "night_temp": str(c.get("nighttemp") or ""),
                    "wind": f'{c.get("daywind") or ""}风{c.get("daypower") or ""}级',
                }
            STATS["ok"] += 1 if data else 0
    except Exception as e:
        STATS["failed"] += 1
        logger.warning("天气请求失败 %s: %s", city, e)
        return {}

    _cache[city] = (now, data)
    return data


def resolve_dates(start_date: str, days: int) -> list[date]:
    """把「出发日期 + 天数」展开成每一天；start_date 缺失或非法时从今天算。"""
    try:
        start = datetime.strptime((start_date or "").strip(), "%Y-%m-%d").date()
    except Exception:
        start = date.today()
    n = max(1, min(int(days or 1), FORECAST_DAYS + 3))
    return [start + timedelta(days=i) for i in range(n)]


def day_tip(city: str, day: date) -> tuple[str, str]:
    """返回 (给用户看的天气文案, 给模型的排程建议)。拿不到就如实说明。"""
    fc = get_forecast(city)
    info = fc.get(day.isoformat())
    if not info:
        if fc and day > max(_parse_day(k) for k in fc if _parse_day(k)):
            STATS["days_out_of_range"] += 1
            return (f"{day.isoformat()} 超出可预报范围（预报仅覆盖 {FORECAST_DAYS} 天），"
                    "请出发前再查看实时天气", "")
        return ("暂未获取到当日天气，请以实时预报为准", "")

    text = (f"{day.month}月{day.day}日 {info['day_weather']}转{info['night_weather']} "
            f"{info['night_temp']}~{info['day_temp']}℃ {info['wind']}")

    advice = []
    w = info["day_weather"] + info["night_weather"]
    try:
        hi = int(info["day_temp"])
    except Exception:
        hi = None
    if any(x in w for x in ("雨", "雪")):
        advice.append("当日有降水，优先安排博物馆/街区/室内景点，取消游船等水上项目")
    if hi is not None and hi >= 35:
        advice.append("高温，户外景点安排在上午10点前或傍晚后，正午安排室内或休息")
    elif hi is not None and hi <= 5:
        advice.append("低温，行程收紧、缩短户外停留并安排室内取暖点")
    if "风" in info.get("wind", "") and any(x in info["wind"] for x in ("5", "6", "7", "8")):
        advice.append("风力较大，取消登山、游船等高空水上项目")
    return text, "；".join(advice)


def trip_weather_block(city: str, start_date: str, days: int) -> str:
    """给 prompt 用的逐日天气段。无数据时返回空串，让调用方保持原有行为。"""
    lines = []
    for i, d in enumerate(resolve_dates(start_date, days), 1):
        text, advice = day_tip(city, d)
        lines.append(f"第{i}天({d.isoformat()}): {text}" + (f" ｜排程建议：{advice}" if advice else ""))
    real = [ln for ln in lines if "暂未获取到" not in ln and "超出可预报范围" not in ln]
    if not real:
        return ""
    return "\n【真实天气·必须原样使用，禁止自行编造天气】\n" + "\n".join(lines) + "\n"


def apply_to_trip(trip_content: dict, city: str, start_date: str, days: int) -> int:
    """用真实预报强制覆盖每天的 weather_tip，返回被覆盖的天数。"""
    covered = 0
    dates = resolve_dates(start_date, days)
    for i, day in enumerate(trip_content.get("itinerary") or []):
        d = dates[i] if i < len(dates) else None
        if not d:
            continue
        text, _ = day_tip(city, d)
        day["weather_tip"] = text
        covered += 1
    return covered

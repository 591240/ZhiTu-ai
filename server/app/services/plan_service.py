import json
import logging
import re
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from app.ai.llm_client import llm_client
from app.config import settings
from app.services import image_service, route_service, weather_service
from kb import candidates
from kb.retriever import detect_city

logger = logging.getLogger(__name__)

# ===== 景点库语料：数据在 kb/corpus/city_spots.json，代码只负责加载 =====
# 保留 SPOTS 这个名字和结构不变：ocr_service 与 template_service.seed 直接用它，
# 且 tests/test_local_generator.py 的断言以本地生成器输出为准。
_CORPUS_FILE = Path(__file__).resolve().parents[2] / 'kb' / 'corpus' / 'city_spots.json'


def _load_spots() -> dict:
    with _CORPUS_FILE.open(encoding='utf-8') as f:
        return json.load(f)


SPOTS = _load_spots()

GENERIC = {
    "popular": [
        [
            {"name": "{city}博物馆", "address": "{city}市中心", "time_slot": "morning", "duration_min": 150, "ticket_price": 0, "category": "人文历史", "description": "了解城市历史的好去处。"},
            {"name": "{city}中央公园", "address": "{city}新区", "time_slot": "afternoon", "duration_min": 140, "ticket_price": 0, "category": "自然风光", "description": "城市绿肺，适合散步。"},
        ],
        [
            {"name": "{city}老街", "address": "{city}老城区", "time_slot": "evening", "duration_min": 120, "ticket_price": 0, "category": "美食", "description": "本地小吃与夜市。"},
        ],
    ],
    "niche": [
        [
            {"name": "{city}近郊徒步线", "address": "{city}郊外", "time_slot": "morning", "duration_min": 200, "ticket_price": 0, "category": "自然风光", "description": "避开人流的秘境路线。"},
        ],
        [
            {"name": "{city}独立书店", "address": "{city}文艺街区", "time_slot": "afternoon", "duration_min": 120, "ticket_price": 0, "category": "休闲度假", "description": "城市文化角落。"},
        ],
    ],
    "meals": [
        {"name": "{city}特色菜馆", "type": "lunch", "avg_price": 80, "specialty": "本地招牌菜", "address": "市中心"},
        {"name": "{city}夜市", "type": "dinner", "avg_price": 60, "specialty": "街头小吃", "address": "老城区"},
    ],
}


def _fill(tpl, city):
    return _fill_obj(tpl, city)


def _fill_obj(obj, city):
    if isinstance(obj, str):
        return obj.replace("{city}", city)
    if isinstance(obj, list):
        return [_fill_obj(x, city) for x in obj]
    if isinstance(obj, dict):
        return {k: _fill_obj(v, city) for k, v in obj.items()}
    return obj


def _build_transport(nodes: list, city: str, transport_mode: str) -> list:
    """
    根据当天节点（景点/餐饮）按时间顺序生成市内交通段。
    公共交通/混合：优先调用高德公交路径规划获取真实线路/车次；
    自驾/步行：回退到简化估算。
    """
    transport = []
    mode = transport_mode or "地铁"
    use_route = "公共" in mode or "混合" in mode
    prev = "酒店"
    for n in nodes:
        if n["name"] == prev:
            continue
        if use_route:
            route = route_service.get_transit_route(prev, n["name"], city, mode)
            if route:
                transport.append({
                    "from": prev,
                    "to": n["name"],
                    "mode": route["mode"],
                    "duration_min": route["duration_min"],
                    "cost": route["cost"],
                    "detail": route["detail"],
                    "segments": route["segments"],
                })
                prev = n["name"]
                continue
        # 步行/自驾/公交查询失败时的兜底
        if "步行" in mode:
            transport.append({"from": prev, "to": n["name"], "mode": "步行", "duration_min": 15, "cost": 0, "detail": f"步行约15分钟从{prev}到{n['name']}"})
        elif "自驾" in mode:
            transport.append({"from": prev, "to": n["name"], "mode": "驾车", "duration_min": 20, "cost": 10, "detail": f"自驾/打车约20分钟从{prev}到{n['name']}"})
        else:
            transport.append({"from": prev, "to": n["name"], "mode": "公交", "duration_min": 30, "cost": 2, "detail": f"建议乘坐公交从{prev}到{n['name']}，约30分钟"})
        prev = n["name"]
    if nodes:
        if use_route:
            route = route_service.get_transit_route(prev, "酒店", city, mode)
            if route:
                transport.append({
                    "from": prev,
                    "to": "酒店",
                    "mode": route["mode"],
                    "duration_min": route["duration_min"],
                    "cost": route["cost"],
                    "detail": route["detail"],
                    "segments": route["segments"],
                })
                return transport
        if "步行" in mode:
            transport.append({"from": prev, "to": "酒店", "mode": "步行", "duration_min": 15, "cost": 0, "detail": f"步行约15分钟从{prev}返回酒店"})
        elif "自驾" in mode:
            transport.append({"from": prev, "to": "酒店", "mode": "驾车", "duration_min": 20, "cost": 10, "detail": f"自驾/打车约20分钟从{prev}返回酒店"})
        else:
            transport.append({"from": prev, "to": "酒店", "mode": "公交", "duration_min": 30, "cost": 2, "detail": f"建议乘坐公交从{prev}返回酒店，约30分钟"})
    return transport


def gen_trip(p: dict) -> dict:
    city = p.get("city") or "杭州"
    # 注意别写成 int(p.get("days") or 2)：那样 days=0 会被 falsy 判断悄悄变成 2 天行程
    raw_days = p.get("days")
    days = max(1, min(int(raw_days) if raw_days not in (None, "") else 2, 4))
    route_type = "niche" if p.get("route_type") == "niche" else "popular"
    repo = SPOTS.get(city)
    base = repo if repo else GENERIC
    day_plans = base["niche"] if route_type == "niche" else base["popular"]
    meals = base["meals"]

    budget_min = int(p.get("budget_min") or 500)
    budget_max = int(p.get("budget_max") or 1500)
    if budget_max < budget_min:
        budget_max = budget_min
    per_day_avg = (budget_min + budget_max) // 2 // days

    itinerary = []
    total = 0
    slot_order = {"morning": 0, "afternoon": 1, "evening": 2}
    slot_start = {"morning": 540, "afternoon": 840, "evening": 1110}
    meal_time = {"breakfast": 480, "lunch": 750, "dinner": 1140}

    def to_hhmm(m):
        return f"{m // 60:02d}:{m % 60:02d}"

    meals_by_type = {"breakfast": [], "lunch": [], "dinner": []}
    for _m in meals:
        meals_by_type.setdefault(_m.get("type"), []).append(_m)

    for i in range(1, days + 1):
        plan = day_plans[(i - 1) % len(day_plans)]
        raw = plan if repo else _fill_obj(plan, city)
        raw = [dict(s) for s in raw]
        raw.sort(key=lambda s: slot_order.get(s.get("time_slot"), 0))
        slot_next = dict(slot_start)
        spots = []
        for s in raw:
            _fill_photo(s)
            info = image_service.get_spot_info(s.get("name", ""), city) or {}
            s["image"] = info.get("image") or ""
            s["location"] = info.get("location") or ""
            slot = s.get("time_slot", "morning")
            start = slot_next[slot]
            s["start_time"] = to_hhmm(start)
            slot_next[slot] = start + int(s.get("duration_min", 120)) + 30
            s.setdefault("best_price", s.get("ticket_price", 0))
            if s.get("ticket_price", 0) > 0:
                s["ticket_channel"] = "景区官方" if s.get("official_account") else "美团"
            spots.append(s)
        types = ["lunch", "dinner", "breakfast"]
        t1 = types[(i - 1) % 3]
        t2 = types[i % 3]
        day_meals = []
        for _t in (t1, t2):
            _arr = meals_by_type.get(_t) or []
            if not _arr:
                continue
            _mm = _fill_obj(dict(_arr[(i - 1) % len(_arr)]), city)
            _mm["start_time"] = to_hhmm(meal_time.get(_t, 750))
            _mm.setdefault("deal_channel", "美团")
            day_meals.append(_mm)
        nodes = [{"name": s["name"], "time": s["start_time"]} for s in spots]
        nodes += [{"name": _m["name"], "time": _m["start_time"]} for _m in day_meals]
        nodes.sort(key=lambda n: n["time"])
        transport = _build_transport(nodes, city, p.get("transport_mode") or "地铁")
        budget = max(100, per_day_avg + (i % 3 - 1) * 30)
        total += budget
        itinerary.append({
            "day_number": i,
            "date_label": f"第{i}天",
            "weather_tip": "建议出行前关注当地天气预报，备好相应装备",
            "season_tip": "热门景点建议错峰，早到可避开人流",
            "crowd_tip": "优先选择开园/开门首时段游览",
            "spots": spots,
            "meals": day_meals,
            "transport": transport,
            "budget": budget,
            "tips": "• 出行前查看天气，备好舒适鞋\n• 热门景点建议错峰前往" if i == 1 else "• 注意保管随身物品\n• 用餐可参考本地人排队店铺",
        })

    title = f"{city}{days}日{'小众深度' if route_type == 'niche' else '经典大众'}游"
    return {
        "title": title,
        "city": city,
        "days": days,
        "route_type": route_type,
        "crowd_type": p.get("crowd_type") or "朋友",
        "budget_min": budget_min,
        "budget_max": budget_max,
        "budget_level": "经济" if budget_max < 500 else "高端" if budget_max > 1500 else "舒适",
        "content": {
            "itinerary": itinerary,
            "total_budget": total,
            "transport_plans": [],
            "budget_analysis": f"预估人均总花费约 ¥{total}，按您设置的 ¥{budget_min}-¥{budget_max}/人预算规划，含景点门票、餐饮与市内交通，仅供参考。",
            "preparations": cross_border_preparations(city),
        },
    }


# 跨境/特殊地区行前准备示例（港澳通行证、签证、电话卡等）
def cross_border_preparations(city: str) -> list:
    c = (city or "").replace("{city}", "").strip()
    if "香港" in c:
        return [
            {"icon": "🛂", "title": "办理港澳通行证及签注", "detail": "需持有效港澳通行证并办理赴港签注（个人游G签或团队游L签），建议提前10个工作日办理。"},
            {"icon": "📱", "title": "电话卡 / 漫游", "detail": "提前开通港澳台漫游或购买香港本地电话卡，确保地图、打车、导航可用。"},
            {"icon": "💳", "title": "货币与支付", "detail": "香港使用港币，八达通/支付宝香港/微信香港钱包通用，建议备少量现金。"},
            {"icon": "🔌", "title": "转换插头", "detail": "英标插头（三方脚），电压220V，出行前备好转换头。"},
        ]
    if "澳门" in c:
        return [
            {"icon": "🛂", "title": "办理港澳通行证及签注", "detail": "需持有效港澳通行证并办理赴澳签注，建议提前10个工作日办理。"},
            {"icon": "📱", "title": "电话卡 / 漫游", "detail": "提前开通港澳台漫游或购买澳门本地电话卡。"},
            {"icon": "💳", "title": "货币与支付", "detail": "澳门使用澳门元/港币，多数商户支持支付宝微信，建议备少量现金。"},
            {"icon": "🔌", "title": "转换插头", "detail": "英标插头，电压220V，备好转换头。"},
        ]
    if "台湾" in c:
        return [
            {"icon": "🛂", "title": "办理入台证", "detail": "需大通证+入台证（通过有资质的旅行社办理），提前2-3周准备。"},
            {"icon": "📱", "title": "电话卡 / 漫游", "detail": "开通港澳台漫游或购买台湾本地电话卡。"},
            {"icon": "💳", "title": "货币与支付", "detail": "台湾使用新台币，街口/Line Pay常用，备少量现金。"},
            {"icon": "🔌", "title": "转换插头", "detail": "美标插头，电压110V，需转换头+变压器。"},
        ]
    return []


def _fill_photo(spot: dict) -> dict:
    s = dict(spot)
    s.setdefault("photo_spots", [{
        "position": "景区标志性观景点",
        "best_time": "上午或日落",
        "tip": "利用自然光拍出通透感",
        "avoid_crowd": "开园首小时抵达",
        "day_night": "日",
        "suitable_for": "所有人",
    }])
    return s


SCHEMA_HINT = """你是专业旅游行程规划师。严格只输出如下 JSON 结构（不要任何多余文字或解释）：
{
  "title":"行程标题",
  "city":"城市",
  "days":2,
  "route_type":"popular 或 niche",
  "crowd_type":"人群类型",
  "budget_min":500,
  "budget_max":1500,
  "content":{
    "transport_plans":[
      {"name":"省时方案","mode":"高铁/飞机/自驾/大巴","price":1200,"duration":"约3小时","pros":"最快到达","cons":"价格较高","arrival_note":"抵达后建议先到酒店寄存行李再游玩"}
    ],
    "itinerary":[
      {
        "day_number":1,
        "date_label":"第1天",
        "weather_tip":"留空即可，系统会用真实天气预报覆盖此字段，禁止自行编造天气",
        "season_tip":"当前为旺季/淡季，热门景点人多，建议错峰",
        "crowd_tip":"建议上午9点前到达避开人流高峰",
        "spots":[
          {"name":"景点名","address":"地址","time_slot":"morning/afternoon/evening","duration_min":120,"ticket_price":0,"best_price":0,"ticket_channel":"景区官方/携程/美团/抖音团购（AI预估最划算购票渠道）","need_booking":False,"official_account":"公众号名称|gh_xxx（若能查到原始ID则填原始ID，否则只填名称）","category":"自然风光/人文历史/美食/网红打卡/休闲度假","description":"一句话简介","photo_spots":[{"position":"观景台东侧","best_time":"日出/日落/上午/下午/夜晚","tip":"详细拍照攻略：说清楚具体机位、推荐构图（三分法/对称/框架/引导线）、最佳光线方向与时段、建议焦段或手机拍摄要点、人物站位与姿态、最终出片氛围，50-80字","avoid_crowd":"开园前30分钟抵达","day_night":"日/夜","suitable_for":"摄影爱好者/家庭/情侣"}],"nearby_food":{"name":"景点附近餐厅名","type":"lunch/dinner/breakfast","avg_price":80,"specialty":"招牌菜","address":"与景点同区域或步行可达的地址","deal_channel":"美团/大众点评/抖音团购"}}
        ],
        "meals":[{"name":"餐厅名","type":"lunch/dinner/breakfast","avg_price":80,"deal_channel":"美团/大众点评/抖音团购（AI预估最划算团购渠道）","specialty":"招牌菜","address":"地址"}],
        "transport":[{"from":"酒店","to":"景点","mode":"地铁/公交/步行/打车","duration_min":30,"cost":5}],
        "budget":500,
        "tips":"当日实用提示"
      }
    ],
    "total_budget":1500,
    "budget_analysis":"总预算构成说明：门票约X元、餐饮约Y元、市内交通约Z元、人均约W元，并说明省钱/升级建议",
    "preparations":[
      {"icon":"🛂","title":"办理港澳通行证及签注","detail":"前往香港/澳门需持有效港澳通行证并办理赴港/澳签注（个人游G签或团队游L签），建议提前10个工作日办理"},
      {"icon":"📱","title":"电话卡 / 漫游","detail":"提前开通港澳台漫游或购买当地电话卡，确保导航、打车、地图可用"}
    ]
  }
}
价格与渠道规则：门票/餐饮请基于常识给出 AI 预估最优价（景点用 ticket_price/best_price，餐饮用 avg_price），并为每个收费景点与每餐推荐一个最划算的购买/团购渠道——景点填 ticket_channel、餐饮填 deal_channel，取值从 {景区官方, 携程, 美团, 飞猪, 同程, 抖音团购, 大众点评} 中选最划算的一个；前端将据此展示「AI 推荐 ¥X · 去XX购买」并一键跳转比价/购买。价格仅为 AI 预估，实际以下单页为准。
要求：transport_plans 必须恰好给出 3 套方案，分别命名为「省时方案」「性价比方案」「舒适方案」，覆盖往返大交通；每个景点至少给出 1 个 photo_spots 打卡机位，热门/标志性景点给出 2-3 个不同机位；photo_spots 的 tip 必须详细具体，避免空泛；weather_tip/season_tip/crowd_tip 每日均需填写；每个 spot 的 nearby_food 必须是该景点附近或同区域、可顺路用餐的餐厅/小吃，不得把全天唯一餐厅重复填给每个景点。
重要约束：itinerary 里的每个 spot 必须是真实可游览的景点或体验（景区、街区、博物馆、自然风光、市集、演出等），严禁把火车站/高铁站/机场/地铁站/汽车站/码头/仅用于住宿的酒店等交通站点或住宿设施当作景点写入 spots；往返与市内交通一律放进 transport 字段（由系统按时间轴自动串接），不要把「前往车站」「入住酒店」列为景点。每天建议安排 2-3 个景点 + 1-2 餐，并为每个 spot 标注 start_time（HH:MM，如 09:00）与精确时长 duration_min，便于前端渲染当日时间轴。
行前准备规则（务必遵守）：若目的地为港澳台或出境（如香港、澳门、国外城市），必须在 content.preparations 中列出该目的地行前必办事项，至少覆盖：①证件（护照/签证、港澳通行证及签注）；②电话卡或国际漫游；③货币与移动支付的跨境使用；④转换插头/电压；⑤海关与防疫注意事项。每项含 icon（emoji）、title、detail 三个字段，detail 为可操作的具体提醒。若目的地为国内大陆城市，preparations 返回空数组 []。"""


def _season_crowd_hint(p: dict) -> str:
    """基于出发日期（按月+节假日）推算季节/客流适配规则，零 API 成本。"""
    import datetime as _dt
    today = _dt.date.today()
    sd = (p or {}).get("start_date") or ""
    try:
        d = _dt.datetime.strptime(sd, "%Y-%m-%d").date()
    except Exception:
        d = today
    month = d.month
    if month in (12, 1, 2):
        season = "冬季"
    elif month in (3, 4, 5):
        season = "春季"
    elif month in (6, 7, 8):
        season = "夏季"
    else:
        season = "秋季"
    peak = (month in (7, 8)
            or (month == 10 and 1 <= d.day <= 7)
            or (month == 5 and 1 <= d.day <= 5)
            or (month == 1 and 25 <= d.day <= 31)
            or (month == 2 and d.day <= 15))
    peak_label = "旺季（人多价高）" if peak else "淡季/平季（人流较少）"
    is_weekend = d.weekday() >= 5
    crowd = "周末出行，热门景点人流偏大" if is_weekend else "工作日出行，相对宽松"
    rules = (
        "环境适配硬规则（务必在输出中体现）："
        "①若为雨天方案优先安排室内景点；"
        "②夏季高温日将户外景点安排在上午或傍晚，避开10:00-16:00；"
        "③大风/恶劣天气取消登山、游船等高危项目；"
        "④旺季主动推荐错峰时段与小众机位，减少排队。"
    )
    return f"环境背景：出发月份推算为{season}、{peak_label}、{crowd}。\n{rules}"


def _local_trip(p: dict) -> dict:
    """本地生成器 + 真实天气覆盖。同步阻塞，调用方必须用 run_in_threadpool。"""
    trip = gen_trip(p)
    weather_service.apply_to_trip(
        trip.get("content") or {}, p.get("city", ""), p.get("start_date") or "", p.get("days") or 2
    )
    return trip


class PlanService:
    """行程生成/微调。

    注意：本模块的同步链路（gen_trip / _normalize / _build_transport）内部会调
    image_service、route_service、weather_service——它们都是同步 requests。
    所有调用点必须走 run_in_threadpool，否则会把 uvicorn 的唯一事件循环卡死
    （一次 2 天行程冷缓存约 15~20 次串行外部请求）。
    """

    async def generate_from_form(self, req) -> dict:
        p = req.model_dump()
        if settings.llm_api_key:
            try:
                data = await llm_client.generate_json(self._form_prompt(p))
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    return await run_in_threadpool(self._normalize, data, p)
                logger.warning("LLM 返回结构异常，回退示例生成：%s", data)
            except Exception:
                logger.exception("LLM 调用失败，回退示例生成")
        return await run_in_threadpool(_local_trip, p)

    async def generate_from_quick(self, text: str) -> dict:
        if settings.llm_api_key:
            try:
                data = await llm_client.generate_json(self._quick_prompt(text))
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    return await run_in_threadpool(self._normalize, data, {"city": "杭州", "days": 2})
                logger.warning("LLM 返回结构异常，回退示例生成：%s", data)
            except Exception:
                logger.exception("LLM 调用失败，回退示例生成")
        city = "杭州"
        for c in SPOTS.keys():
            if c in text:
                city = c
                break
        m = re.search(r"(\d+)\s*天", text)
        days = int(m.group(1)) if m else 2
        route_type = "niche" if any(w in text for w in ["小众", "深度", "冷门"]) else "popular"
        return await run_in_threadpool(
            _local_trip, {"city": city, "days": days, "route_type": route_type, "transport_mode": "地铁"}
        )

    def _form_prompt(self, p):
        prefs = ",".join(p.get("preferences") or [])
        env_hint = _season_crowd_hint(p)
        return SCHEMA_HINT + (
            f"\n参数：目的地={p.get('city')}，出发地={p.get('departure_city') or '未指定'}，"
            f"天数={p.get('days')}，人群={p.get('crowd_type')}，人数={p.get('people_count') or 2}人，"
            f"预算范围={p.get('budget_min', 0)}-{p.get('budget_max', 0)}元/人，偏好={prefs}，市内交通={p.get('transport_mode')}，"
            f"往返偏好={p.get('transport_preference') or '未指定'}，"
            f"出发日期={p.get('start_date') or '未指定'}，返程日期={p.get('end_date') or '未指定'}，"
            f"路线={p.get('route_type')}，备注={p.get('remark', '')}。"
            f"必看风景/必去地点={p.get('must_see') or '未指定'}。"
            f"{self._pool_hint(p.get('city'))}"
            f"{self._weather_hint(p)}"
            f"\n{env_hint}\n只输出JSON。"
        )

    def _quick_prompt(self, text):
        env_hint = _season_crowd_hint({})
        city = detect_city(text) or ""
        m = re.search(r"(\d+)\s*天", text or "")
        days = int(m.group(1)) if m else 2
        weather_hint = self._weather_hint({"city": city, "days": days}) if city else ""
        return SCHEMA_HINT + f"\n用户需求：{text}。{self._pool_hint(city)}{weather_hint}{env_hint}\n只输出JSON。"

    @staticmethod
    def _weather_hint(p) -> str:
        """真实逐日天气。拿不到时返回空串——宁可没有，也不让模型编。"""
        return weather_service.trip_weather_block(
            p.get("city") or "", p.get("start_date") or "", p.get("days") or 2
        )

    @staticmethod
    def _pool_hint(city: str) -> str:
        """把真实候选景点写进 prompt——模型只能从名单里选，从源头掐掉编造景点。

        名单为空（既不在 9 城语料又拿不到高德）时返回空串，退回原有行为，
        绝不因为拿不到名单而让整次生成失败。
        """
        pool = candidates.city_pool(city) if city else []
        if not pool:
            return ""
        return (
            "\n【候选景点·真实名单】spots 的 name 必须严格从下面名单中选择，"
            "不得新增、改写或拼凑名单外的名称（用户在「必去地点」里点名的除外）：\n"
            + candidates.format_pool(pool) + "\n"
        )

    def _normalize(self, data, p):
        data.setdefault("title", f"{p.get('city', '')}行程")
        data.setdefault("city", p.get("city", "杭州"))
        data.setdefault("days", p.get("days", 2))
        data.setdefault("route_type", p.get("route_type", "popular"))
        data.setdefault("crowd_type", p.get("crowd_type", "朋友"))
        data.setdefault("budget_min", p.get("budget_min", 500))
        data.setdefault("budget_max", p.get("budget_max", 1500))
        # 兼容旧字段与前端展示：根据预算范围自动映射档位标签
        _max = data.get("budget_max") or 1500
        data.setdefault("budget_level", "经济" if _max < 500 else "高端" if _max > 1500 else "舒适")
        content = data.setdefault("content", {})
        content.setdefault("itinerary", [])
        content.setdefault("total_budget", 0)
        content.setdefault("transport_plans", [])
        content.setdefault("budget_analysis", "")
        content.setdefault("preparations", [])
        trip_city = data.get("city", "")
        # 后置校验：把 LLM 编出来的、不在真实候选池里的景点换掉；池为空时原样不动。
        # 校验结果只在本请求内使用——曾经写成类属性 self.last_verify，并发时会串用户。
        verify = candidates.verify_itinerary(content, trip_city, p.get("must_see") or "")
        if verify.get("replaced"):
            logger.info("行程景点校验：替换 %s 个 / 校验 %s 个", verify["replaced"], verify["checked"])
        for day in content["itinerary"]:
            day.setdefault("weather_tip", "")
            day.setdefault("season_tip", "")
            day.setdefault("crowd_tip", "")
            day.setdefault("spots", [])
            day.setdefault("meals", [])
            day.setdefault("transport", [])
            day.setdefault("budget", 0)
            day.setdefault("tips", "")
            for spot in day["spots"]:
                spot.setdefault("photo_spots", [])
                spot.setdefault("duration_min", 120)
                spot.setdefault("ticket_price", 0)
                spot.setdefault("best_price", spot.get("ticket_price", 0))
                spot.setdefault("ticket_channel", "")
                spot.setdefault("need_booking", False)
                spot.setdefault("official_account", "")
                spot.setdefault("description", "")
                spot.setdefault("category", "")
                spot.setdefault("address", "")
                spot.setdefault("nearby_food", None)
                if not spot.get("image") or not spot.get("location"):
                    try:
                        info = image_service.get_spot_info(spot.get("name", ""), trip_city) or {}
                        if not spot.get("image"):
                            spot["image"] = info.get("image") or ""
                        if not spot.get("location"):
                            spot["location"] = info.get("location") or ""
                    except Exception:
                        logger.exception("获取景点信息失败: %s / %s", trip_city, spot.get("name", ""))
                for ps in spot["photo_spots"]:
                    ps.setdefault("position", "")
                    ps.setdefault("best_time", "")
                    ps.setdefault("tip", "")
                    ps.setdefault("avoid_crowd", "")
                    ps.setdefault("day_night", "")
                    ps.setdefault("suitable_for", "")
            for meal in day["meals"]:
                meal.setdefault("deal_channel", "")
                meal.setdefault("avg_price", 0)
                meal.setdefault("specialty", "")
                meal.setdefault("address", "")
                meal.setdefault("type", "lunch")
            # 用真实公交/步行路线重建市内交通段（高德失败时降级为空列表，不阻塞整体返回）
            try:
                nodes = [{"name": s["name"], "time": s.get("start_time", "09:00")} for s in day["spots"]]
                nodes += [{"name": m["name"], "time": m.get("start_time", "12:00")} for m in day["meals"]]
                nodes.sort(key=lambda n: n["time"])
                day["transport"] = _build_transport(nodes, trip_city, p.get("transport_mode") or "地铁")
            except Exception:
                logger.exception("生成市内交通段失败: %s", trip_city)
                day["transport"] = []
        # 天气是事实字段：无论模型写了什么，都用真实预报覆盖
        weather_service.apply_to_trip(
            content, trip_city, p.get("start_date") or "", p.get("days") or data.get("days") or 2
        )
        return data

    # ===== Function Calling 微调（工具调用）=====
    # 模型不再重写整份行程 JSON，而是调用 apply_edits 工具提交结构化局部编辑，
    # 由 _apply_edits 确定性执行：未提及的内容一个字段都不会动，景点名被候选池硬约束。
    _EDIT_TOOL = {
        "type": "function",
        "function": {
            "name": "apply_edits",
            "description": "对现有行程提交一组局部修改。系统会按顺序确定性地执行每条编辑，"
                           "你只需描述改什么，不需要重排其余内容、不需要输出完整行程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string", "description": "一句话中文说明本轮做了哪些改动"},
                    "edits": {
                        "type": "array",
                        "description": "编辑列表，按执行顺序排列",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["add_spot", "remove_spot", "replace_spot",
                                             "add_meal", "remove_meal", "replace_meal"],
                                    "description": "编辑类型：加/删/换景点，加/删/换餐厅",
                                },
                                "day": {"type": "integer", "description": "第几天，从 1 开始"},
                                "index": {"type": "integer",
                                          "description": "当天 spots/meals 数组下标，从 0 开始；替换/删除必填，新增可省略（追加到末尾）"},
                                "name": {"type": "string",
                                         "description": "add_spot/replace_spot 的景点名，必须严格取自候选名单"},
                                "meal": {
                                    "type": "object",
                                    "description": "add_meal/replace_meal 的餐厅信息",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string", "enum": ["breakfast", "lunch", "dinner"]},
                                        "avg_price": {"type": "number"},
                                        "specialty": {"type": "string"},
                                        "address": {"type": "string"},
                                    },
                                    "required": ["name"],
                                },
                            },
                            "required": ["action", "day"],
                        },
                    },
                },
                "required": ["reply", "edits"],
            },
        },
    }

    async def _adjust_via_tools(self, trip: dict, instruction: str):
        """工具化微调：返回 (reply, new_trip)；模型没提交有效编辑时返回 None（走旧链路）。"""
        data = await llm_client.generate_tool_call(
            "你是旅游行程微调助手，通过调用 apply_edits 工具提交对行程的局部修改。",
            self._adjust_tools_prompt(trip, instruction),
            [self._EDIT_TOOL],
        )
        if not data:
            return None
        edits = data.get("edits") or []
        reply = (data.get("reply") or "").strip()
        if not isinstance(edits, list) or not edits:
            return None
        # 深拷贝：编辑执行失败不能污染调用方手里的原行程
        new_trip = json.loads(json.dumps(trip, ensure_ascii=False))
        applied, touched = self._apply_edits(new_trip, edits, instruction)
        if not applied:
            return None
        logger.info("工具化微调应用 %s 条编辑：%s", len(applied), applied)
        new_trip = await run_in_threadpool(self._normalize_adjust, new_trip, instruction)
        self._rebuild_transport_for(new_trip, touched)
        if trip.get("id") is not None:
            new_trip["id"] = trip["id"]
        return reply or "已按你的要求调整行程。", new_trip

    def _adjust_tools_prompt(self, trip: dict, instruction: str) -> str:
        return (
            "当前用户行程 JSON：\n"
            f"{json.dumps(trip, ensure_ascii=False)}\n\n"
            f"用户希望做的修改：{instruction}\n\n"
            f"{self._pool_hint(trip.get('city') or '')}"
            "规则：\n"
            "1. 只提交用户要求的改动，不要提交任何没被要求的编辑。\n"
            "2. add_spot/replace_spot 的 name 必须严格取自候选名单；名单里没有且用户没点名的景点不得引入。\n"
            "3. day 从 1 开始；index 是当天 spots/meals 数组的下标（从 0 开始），替换/删除时必填，不确定就先数一数。\n"
            "4. 若指令无法对应任何具体编辑，edits 返回空数组并在 reply 中说明。\n"
            "5. 只调用一次 apply_edits。"
        )

    def _apply_edits(self, trip: dict, edits: list, instruction: str = ""):
        """确定性执行编辑列表，返回 (已执行的描述列表, 被改动天的下标集合)。

        校验规则与全量微调一致：池外且用户没点名的景点直接拒绝；
        用户点名的先放行，交给 _normalize_adjust 里的 verify_itinerary 做 POI 复核。
        """
        city = trip.get("city") or ""
        content = trip.setdefault("content", {})
        days = content.setdefault("itinerary", [])
        pool = candidates.city_pool(city) if city else []
        applied, touched = [], set()
        for e in edits:
            if not isinstance(e, dict):
                continue
            action = e.get("action")
            try:
                d = int(e.get("day")) - 1
            except (TypeError, ValueError):
                continue
            if d < 0 or d >= len(days):
                continue
            day = days[d]
            spots = day.setdefault("spots", [])
            meals = day.setdefault("meals", [])
            try:
                i = int(e["index"]) if e.get("index") is not None else None
            except (TypeError, ValueError):
                i = None

            if action in ("add_spot", "replace_spot"):
                raw_name = (e.get("name") or "").strip()
                if not raw_name:
                    continue
                item = candidates.find(pool, raw_name) if pool else None
                # 池外且用户没点名 → 拒绝，绝不引入编造景点
                if pool and not item and raw_name not in (instruction or ""):
                    logger.info("工具化微调拒绝池外景点: %s", raw_name)
                    continue
                if action == "add_spot":
                    spot = self._spot_from_pool(item, raw_name, self._next_start_time(day))
                    spots.append(spot)
                    applied.append(f"D{d + 1} 添加景点 {spot['name']}")
                else:
                    if i is None or not (0 <= i < len(spots)):
                        continue
                    spot = self._spot_from_pool(item, raw_name, spots[i].get("start_time", "09:00"))
                    # 旧景点的图和坐标可复用（同类位置），缺失的走默认占位
                    spot.setdefault("image", spots[i].get("image") or "")
                    spot.setdefault("location", spots[i].get("location") or "")
                    spots[i] = spot
                    applied.append(f"D{d + 1} 景点[{i}] 换成 {spot['name']}")
            elif action == "remove_spot":
                if i is None or not (0 <= i < len(spots)):
                    continue
                applied.append(f"D{d + 1} 删除景点 {spots[i].get('name', i)}")
                spots.pop(i)
            elif action in ("add_meal", "replace_meal"):
                m = e.get("meal") or {}
                name = (m.get("name") or "").strip()
                if not name:
                    continue
                meal = {
                    "name": name,
                    "type": m.get("type") or "lunch",
                    "avg_price": m.get("avg_price") or 0,
                    "specialty": m.get("specialty") or "",
                    "address": m.get("address") or "",
                }
                if action == "add_meal":
                    meal["start_time"] = self._next_start_time(day, 90)
                    meals.append(meal)
                    applied.append(f"D{d + 1} 添加餐厅 {name}")
                else:
                    if i is None or not (0 <= i < len(meals)):
                        continue
                    meal["start_time"] = meals[i].get("start_time", "12:00")
                    meals[i] = meal
                    applied.append(f"D{d + 1} 餐厅[{i}] 换成 {name}")
            elif action == "remove_meal":
                if i is None or not (0 <= i < len(meals)):
                    continue
                applied.append(f"D{d + 1} 删除餐厅 {meals[i].get('name', i)}")
                meals.pop(i)
            else:
                continue
            touched.add(d)
        return applied, touched

    @staticmethod
    def _spot_from_pool(item: dict | None, name: str, start_time: str) -> dict:
        """从候选池条目构造完整景点对象；池外用户点名的给最小骨架，其余字段由 _normalize_adjust 补齐。"""
        if not item:
            return {"name": name, "start_time": start_time}
        spot = {
            "name": item["name"],
            "address": item.get("address", ""),
            "duration_min": item.get("duration_min", 120),
            "ticket_price": item.get("ticket_price", 0),
            "category": item.get("category", ""),
            "description": item.get("description", ""),
            "photo_spots": item.get("photo_spots") or [],
            "need_booking": bool(item.get("need_booking")),
            "official_account": item.get("official_account", ""),
            "start_time": start_time,
        }
        if item.get("location"):
            spot["location"] = item["location"]
        return spot

    @staticmethod
    def _next_start_time(day: dict, duration_min: int = 120) -> str:
        """新增节点的时间：接在当天最晚节点之后，最晚不超过 21:00。"""
        cur = 0
        for n in day.get("spots", []) + day.get("meals", []):
            m = re.match(r"^(\d{1,2}):(\d{2})$", str(n.get("start_time") or ""))
            if m:
                cur = max(cur, int(m.group(1)) * 60 + int(m.group(2)))
        nxt = min(cur + duration_min, 21 * 60)
        return f"{nxt // 60:02d}:{nxt % 60:02d}"

    @staticmethod
    def _rebuild_transport_for(trip: dict, day_idx: set):
        """只重建被改动天的市内交通段，避免交通信息里残留已换掉的旧景点名。"""
        content = trip.get("content") or {}
        days = content.get("itinerary") or []
        city = trip.get("city") or ""
        mode = trip.get("transport_mode") or "地铁"
        for d in day_idx:
            if d >= len(days):
                continue
            day = days[d]
            try:
                nodes = [{"name": s["name"], "time": s.get("start_time", "09:00")}
                         for s in day.get("spots", [])]
                nodes += [{"name": m["name"], "time": m.get("start_time", "12:00")}
                          for m in day.get("meals", [])]
                nodes.sort(key=lambda n: n["time"])
                day["transport"] = _build_transport(nodes, city, mode)
            except Exception:
                logger.exception("微调后重建市内交通失败: day=%s（保留原交通段）", d + 1)

    async def adjust(self, trip: dict, instruction: str):
        """对话微调：携带当前行程上下文，调用 LLM 真正理解并执行修改指令。

        返回 (reply, new_trip)。无 LLM Key 或解析失败时优雅降级（返回原行程 + 提示）。
        """
        trip = trip or {}
        tid = trip.get("id")
        if settings.llm_api_key:
            # 优先 Function Calling：模型只提交结构化局部编辑，改动由代码确定性执行，
            # 不会误伤未提及的内容，景点名受候选池硬约束。
            try:
                result = await self._adjust_via_tools(trip, instruction)
                if result:
                    return result
                logger.info("工具化微调未产生有效编辑，回退全量 JSON 微调")
            except Exception:
                logger.exception("Function Calling 微调失败，回退全量 JSON 微调")
            try:
                data = await llm_client.generate_json(self._adjust_prompt(trip, instruction))
                # LLM 返回 { reply, title, city, days, ..., content }
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    reply = data.pop("reply", "已为你调整行程。")
                    new_trip = await run_in_threadpool(self._normalize_adjust, data, instruction)
                    if tid is not None:
                        new_trip["id"] = tid
                    return reply, new_trip
                logger.warning("LLM 微调返回结构异常，回退原行程：%s", data)
            except Exception:
                logger.exception("LLM 微调调用失败，回退原行程")

        # 降级：诚实提示，不伪造修改（保留原 id 以便前端仍可保存）
        if tid is not None:
            trip = dict(trip)
            trip["id"] = tid
        return (
            "（当前为离线演示模式，未接入大模型，暂无法智能微调行程。"
            "请在服务端配置 LLM_API_KEY 后重试。）",
            trip,
        )

    def _adjust_prompt(self, trip: dict, instruction: str) -> str:
        trip_json = json.dumps(trip, ensure_ascii=False)
        return (
            "你是旅游行程微调助手。以下是用户现有的行程计划（JSON）：\n"
            f"{trip_json}\n\n"
            f"用户希望做的修改：{instruction}\n\n"
            f"{self._pool_hint(trip.get('city') or '')}"
            "要求：\n"
            "1. 深刻理解指令（替换/新增/删除景点、增减天数、调整时间顺序、替换餐饮、调整预算或节奏等）。\n"
            "2. 返回修改后的【完整行程 JSON】，必须保持原有字段结构（title/city/days/route_type/crowd_type/budget_level/content 等），"
            "content 内每个 spot 至少保留 1 个 photo_spots，不得随意删减字段。\n"
            "3. 在返回 JSON 的顶层增加字段 \"reply\"，用一句话中文说明你做了哪些改动；"
            "若指令无法对应具体改动，请原样返回原行程并在 reply 中说明。\n"
            "4. 新增或替换进去的景点，name 必须严格取自上面的候选名单；名单里没有、用户也没点名的景点一律不得引入。\n"
            "5. 只输出 JSON，不要任何多余文字或解释。"
        )

    def _normalize_adjust(self, data: dict, instruction: str = "") -> dict:
        data.setdefault("title", "我的行程")
        data.setdefault("city", "杭州")
        data.setdefault("days", 2)
        data.setdefault("route_type", "popular")
        data.setdefault("crowd_type", "朋友")
        data.setdefault("budget_min", 500)
        data.setdefault("budget_max", 1500)
        _max = data.get("budget_max") or 1500
        data.setdefault("budget_level", "经济" if _max < 500 else "高端" if _max > 1500 else "舒适")
        content = data.setdefault("content", {})
        content.setdefault("itinerary", [])
        content.setdefault("total_budget", 0)
        content.setdefault("transport_plans", [])
        content.setdefault("budget_analysis", "")
        content.setdefault("preparations", [])
        # 微调同样要校验：模型换景点时最容易塞进池外甚至不存在的名字。
        # 但用户在指令里点名的必须保留，否则"换成海昌海洋公园"会被校验掉。
        verify = candidates.verify_itinerary(content, data.get("city", ""), instruction=instruction)
        if verify.get("replaced"):
            logger.info("微调景点校验：替换 %s 个 / 校验 %s 个", verify["replaced"], verify["checked"])
        for day in content["itinerary"]:
            day.setdefault("weather_tip", "")
            day.setdefault("season_tip", "")
            day.setdefault("crowd_tip", "")
            day.setdefault("spots", [])
            day.setdefault("meals", [])
            day.setdefault("transport", [])
            day.setdefault("budget", 0)
            day.setdefault("tips", "")
            for spot in day["spots"]:
                spot.setdefault("photo_spots", [])
                spot.setdefault("duration_min", 120)
                spot.setdefault("ticket_price", 0)
                spot.setdefault("best_price", spot.get("ticket_price", 0))
                spot.setdefault("ticket_channel", "")
                spot.setdefault("need_booking", False)
                spot.setdefault("official_account", "")
                spot.setdefault("description", "")
                spot.setdefault("category", "")
                spot.setdefault("address", "")
                for ps in spot["photo_spots"]:
                    ps.setdefault("position", "")
                    ps.setdefault("best_time", "")
                    ps.setdefault("tip", "")
                    ps.setdefault("avoid_crowd", "")
                    ps.setdefault("day_night", "")
                    ps.setdefault("suitable_for", "")
            for meal in day["meals"]:
                meal.setdefault("deal_channel", "")
                meal.setdefault("avg_price", 0)
                meal.setdefault("specialty", "")
                meal.setdefault("address", "")
                meal.setdefault("type", "lunch")
        # 微调后同样强制覆盖天气：模型改行程时经常把旧的瞎编文案抄过来
        weather_service.apply_to_trip(
            content, data.get("city", ""), data.get("start_date") or "",
            data.get("days") or len(content["itinerary"]) or 2,
        )
        return data


plan_service = PlanService()

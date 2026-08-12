import json
import logging
import re

from app.ai.llm_client import llm_client
from app.config import settings

logger = logging.getLogger(__name__)

# ===== 景点库（Mock 生成器使用，无 LLM Key 时返回示例行程） =====
SPOTS = {
    "杭州": {
        "popular": [
            [
                {"name": "西湖", "address": "杭州市西湖区龙井路1号", "time_slot": "morning", "duration_min": 180, "ticket_price": 0, "category": "自然风光", "description": "断桥残雪、苏堤春晓，建议骑行或步行环湖。"},
                {"name": "灵隐寺", "address": "杭州市西湖区法云弄1号", "time_slot": "afternoon", "duration_min": 150, "ticket_price": 75, "category": "人文历史", "description": "千年古刹，需先买飞来峰门票再入寺。"},
            ],
            [
                {"name": "西溪湿地", "address": "杭州市西湖区天目山路518号", "time_slot": "morning", "duration_min": 150, "ticket_price": 80, "category": "自然风光", "description": "城市湿地，摇橹船体验最佳。"},
                {"name": "河坊街", "address": "杭州市上城区河坊街", "time_slot": "evening", "duration_min": 120, "ticket_price": 0, "category": "美食", "description": "老字号小吃与伴手礼集中地。"},
            ],
        ],
        "niche": [
            [
                {"name": "九溪烟树", "address": "杭州市西湖区九溪路", "time_slot": "morning", "duration_min": 160, "ticket_price": 0, "category": "自然风光", "description": "本地人私藏徒步路线，林荫溪水。"},
                {"name": "良渚古城遗址", "address": "杭州市余杭区瓶窑镇", "time_slot": "afternoon", "duration_min": 160, "ticket_price": 0, "category": "人文历史", "description": "世界遗产，人少清静。"},
            ],
            [
                {"name": "龙井村", "address": "杭州市西湖区龙井村", "time_slot": "morning", "duration_min": 140, "ticket_price": 0, "category": "休闲度假", "description": "采茶品茗，避开人流。"},
            ],
        ],
        "meals": [
            {"name": "外婆家", "type": "lunch", "avg_price": 80, "specialty": "茶香鸡、麻婆豆腐", "address": "多家分店"},
            {"name": "楼外楼", "type": "dinner", "avg_price": 160, "specialty": "西湖醋鱼、龙井虾仁", "address": "孤山路30号"},
            {"name": "知味观", "type": "breakfast", "avg_price": 30, "specialty": "猫耳朵、小笼", "address": "仁和路83号"},
        ],
    },
    "成都": {
        "popular": [
            [
                {"name": "宽窄巷子", "address": "成都市青羊区金河路口", "time_slot": "morning", "duration_min": 150, "ticket_price": 0, "category": "人文历史", "description": "老成都院落文化代表。"},
                {"name": "锦里", "address": "成都市武侯区武侯祠大街231号", "time_slot": "evening", "duration_min": 120, "ticket_price": 0, "category": "美食", "description": "三国文化+小吃街。"},
            ],
            [
                {"name": "大熊猫繁育研究基地", "address": "成都市成华区熊猫大道1375号", "time_slot": "morning", "duration_min": 200, "ticket_price": 55, "category": "亲子", "description": "早上8点前到可看饲养员喂熊猫。"},
                {"name": "武侯祠", "address": "成都市武侯区武侯祠大街231号", "time_slot": "afternoon", "duration_min": 120, "ticket_price": 50, "category": "人文历史", "description": "中国唯一的君臣合祀祠庙。"},
            ],
        ],
        "niche": [
            [
                {"name": "玉林路小酒馆", "address": "成都市武侯区玉林西路", "time_slot": "evening", "duration_min": 120, "ticket_price": 0, "category": "休闲度假", "description": "赵雷歌声里的小巷，文艺青年聚集。"},
                {"name": "东郊记忆", "address": "成都市成华区建设南支路", "time_slot": "morning", "duration_min": 150, "ticket_price": 0, "category": "人文历史", "description": "旧工厂改造的文创园。"},
            ],
            [
                {"name": "彭镇老茶馆", "address": "成都市双流区彭镇", "time_slot": "morning", "duration_min": 160, "ticket_price": 0, "category": "人文历史", "description": "百年茶馆，老茶客与摄影人。"},
            ],
        ],
        "meals": [
            {"name": "小龙坎火锅", "type": "dinner", "avg_price": 120, "specialty": "牛油锅底、毛肚", "address": "多家分店"},
            {"name": "陈麻婆豆腐", "type": "lunch", "avg_price": 70, "specialty": "麻婆豆腐、回锅肉", "address": "青华路"},
        ],
    },
}

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


def gen_trip(p: dict) -> dict:
    city = p.get("city") or "杭州"
    days = max(1, min(int(p.get("days") or 2), 4))
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
    for i in range(1, days + 1):
        plan = day_plans[(i - 1) % len(day_plans)]
        spots = plan if repo else _fill_obj(plan, city)
        spots = [_fill_photo(s) for s in spots]
        for s in spots:
            s.setdefault("best_price", s.get("ticket_price", 0))
            if s.get("ticket_price", 0) > 0:
                s["ticket_channel"] = "景区官方" if s.get("official_account") else "美团"
        start = (i - 1) % len(meals)
        day_meals = meals[start : start + 1] if repo else _fill_obj(meals[start : start + 1], city)
        for m in day_meals:
            m.setdefault("deal_channel", "美团")
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
            "transport": [
                {"from": "酒店", "to": spots[0]["name"], "mode": p.get("transport_mode") or "地铁", "duration_min": 30, "cost": 5}
            ],
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
        "weather_tip":"今日晴，注意防晒补水（若未知天气则给通用建议）",
        "season_tip":"当前为旺季/淡季，热门景点人多，建议错峰",
        "crowd_tip":"建议上午9点前到达避开人流高峰",
        "spots":[
          {"name":"景点名","address":"地址","time_slot":"morning/afternoon/evening","duration_min":120,"ticket_price":0,"best_price":0,"ticket_channel":"景区官方/携程/美团/抖音团购（AI预估最划算购票渠道）","need_booking":false,"official_account":"","category":"自然风光/人文历史/美食/网红打卡/休闲度假","description":"一句话简介","photo_spots":[{"position":"观景台东侧","best_time":"日出/日落/上午/下午/夜晚","tip":"低角度拍湖面反光更有层次","avoid_crowd":"开园前30分钟抵达","day_night":"日/夜","suitable_for":"摄影爱好者/家庭/情侣"}]}
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
要求：transport_plans 必须恰好给出 3 套方案，分别命名为「省时方案」「性价比方案」「舒适方案」，覆盖往返大交通；每个景点至少给出 1 个 photo_spots 打卡机位；weather_tip/season_tip/crowd_tip 每日均需填写。
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


class PlanService:
    async def generate_from_form(self, req) -> dict:
        if settings.llm_api_key:
            try:
                data = await llm_client.generate_json(self._form_prompt(req.dict()))
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    return self._normalize(data, req.dict())
                logger.warning("LLM 返回结构异常，回退示例生成：%s", data)
            except Exception:
                logger.exception("LLM 调用失败，回退示例生成")
        return gen_trip(req.dict())

    async def generate_from_quick(self, text: str) -> dict:
        if settings.llm_api_key:
            try:
                data = await llm_client.generate_json(self._quick_prompt(text))
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    return self._normalize(data, {"city": "杭州", "days": 2})
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
        return gen_trip({"city": city, "days": days, "route_type": route_type, "transport_mode": "地铁"})

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
            f"\n{env_hint}\n只输出JSON。"
        )

    def _quick_prompt(self, text):
        env_hint = _season_crowd_hint({})
        return SCHEMA_HINT + f"\n用户需求：{text}。{env_hint}\n只输出JSON。"

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
        return data

    async def adjust(self, trip: dict, instruction: str):
        """对话微调：携带当前行程上下文，调用 LLM 真正理解并执行修改指令。

        返回 (reply, new_trip)。无 LLM Key 或解析失败时优雅降级（返回原行程 + 提示）。
        """
        trip = trip or {}
        tid = trip.get("id")
        if settings.llm_api_key:
            try:
                data = await llm_client.generate_json(self._adjust_prompt(trip, instruction))
                # LLM 返回 { reply, title, city, days, ..., content }
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    reply = data.pop("reply", "已为你调整行程。")
                    new_trip = self._normalize_adjust(data)
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
            "要求：\n"
            "1. 深刻理解指令（替换/新增/删除景点、增减天数、调整时间顺序、替换餐饮、调整预算或节奏等）。\n"
            "2. 返回修改后的【完整行程 JSON】，必须保持原有字段结构（title/city/days/route_type/crowd_type/budget_level/content 等），"
            "content 内每个 spot 至少保留 1 个 photo_spots，不得随意删减字段。\n"
            "3. 在返回 JSON 的顶层增加字段 \"reply\"，用一句话中文说明你做了哪些改动；"
            "若指令无法对应具体改动，请原样返回原行程并在 reply 中说明。\n"
            "4. 只输出 JSON，不要任何多余文字或解释。"
        )

    def _normalize_adjust(self, data: dict) -> dict:
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
        return data


plan_service = PlanService()

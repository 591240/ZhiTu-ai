"""离线验证：不依赖外网，验证三个接入点的解析/降级逻辑。

运行：server/venv/Scripts/python.exe tests_offline.py
"""
import asyncio
import json
import sys

from app.services.geocode_service import GeocodeService
from app.services.ticket_service import TicketService
from app.services.ota_service import ota_service

passed = 0
failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}  {extra}")


# ---------- 1) 高德 MCP 解析（官方 maps_geo 真实返回结构）----------
print("\n[1] 高德 MCP geocode 解析")
gs = GeocodeService()
# 官方 Amap maps_geo 返回示例
amap_json = json.dumps({
    "status": "1",
    "geocodes": [{"formatted_address": "浙江省杭州市上城区杭州东站", "location": "120.2120,30.2741"}]
})
loc = gs._parse_gaode(amap_json, "杭州东站")
check("maps_geo geocodes 解析出坐标", loc and abs(loc["lat"] - 30.2741) < 1e-3 and abs(loc["lng"] - 120.2120) < 1e-3, str(loc))
check("source 标记为 gaode-mcp", loc and loc.get("source") == "gaode-mcp")

# 通用 location 字典
loc2 = gs._parse_gaode(json.dumps({"location": {"lng": 116.40, "lat": 39.90}}), "北京")
check("location 字典解析", loc2 and abs(loc2["lat"] - 39.90) < 1e-3)

# 纯文本退化（高德返回 经度,纬度）
loc3 = gs._parse_gaode("坐标：120.2120,30.2741", "杭州东站")
check("纯文本 '经度,纬度' 退化解析", loc3 and abs(loc3["lat"] - 30.2741) < 1e-3 and abs(loc3["lng"] - 120.2120) < 1e-3, str(loc3))

# 无法解析
check("乱码返回 None", gs._parse_gaode("无坐标信息", "火星") is None)

# 降级：无 URL/key 时走内置表（开发期可用）
async def _g():
    return await gs.geocode("杭州东站")
res = asyncio.run(_g())
check("内置表兜底：杭州东站有坐标", res and res["source"].startswith("builtin"), str(res))
res2 = asyncio.run(_g())
check("内置表兜底：北京南站有坐标", res2 and res2["lat"] is not None, str(res2))


# ---------- 2) 12306 车次解析 ----------
print("\n[2] 12306 车次解析")
ts = TicketService()
sample = """G7503 杭州东 06:00 上海虹桥 07:58 二等座 ¥73 一等座 ¥117
D2281 杭州东 07:12 宁波 08:39 二等座 ¥52
G7505 杭州东 08:30 上海虹桥 10:28 商务座 ¥219"""
trains = ts._parse_trains(sample)
check("解析出 3 趟车", len(trains) == 3, str(len(trains)))
check("保留 trainNo", trains[0]["trainNo"] == "G7503")
check("保留 line 原文", "G7503" in trains[0]["line"])
check("提取出发时间", trains[0]["depart"] == "06:00", str(trains[0]))
check("提取到达时间", trains[0]["arrive"] == "07:58", str(trains[0]))
check("提取价格", "73" in trains[0]["prices"], str(trains[0]))

# 降级：无 URL → fallback 不崩
async def _f():
    return await ts.search("2026-09-01", "杭州", "上海")
fb = asyncio.run(_f())
check("无 MCP_URL 时 fallback 不崩", fb and fb["source"] == "fallback", str(fb))


# ---------- 3) OTA 渠道与实时价接入点 ----------
print("\n[3] OTA 渠道层")
ch_t = ota_service.list_channels("ticket", "西湖")
check("门票渠道≥6", len(ch_t) >= 6, str(len(ch_t)))
check("官方渠道 recommend=True", any(c["key"] == "official" and c["recommend"] for c in ch_t))
ct = [c for c in ch_t if c["key"] == "ctrip"][0]
from urllib.parse import unquote
check("携程带搜索深链且含关键词", ct.get("search") and "西湖" in unquote(ct["search"]), str(ct))
check("餐饮渠道含美团/点评", any(c["key"] == "meituan" for c in ota_service.list_channels("food")) and any(c["key"] == "dianping" for c in ota_service.list_channels("food")))
check("酒店渠道含携程/去哪儿", any(c["key"] == "ctrip" for c in ota_service.list_channels("hotel")) and any(c["key"] == "qunar" for c in ota_service.list_channels("hotel")))
pr = ota_service.query_price("ticket", "西湖", "ctrip")
check("实时价接口标记 enterprise_required", pr["available"] is False and pr["reason"] == "enterprise_required", str(pr))


print(f"\n结果：通过 {passed} / 失败 {failed}")
sys.exit(1 if failed else 0)

"""OTA（在线旅游平台）渠道与实时价格接入层。

当前小程序内「门票 / 酒店 / 餐饮」采用「推荐渠道 + 跳转」模式：复制 OTA 搜索链接或官方公众号名，
引导用户在携程 / 美团 / 飞猪 / 同程 / 抖音等 App 内打开比价下单。该模式不需要任何企业资质，
是个体户阶段最稳的导流 / 变现方式。

实时票价 / 酒店价格 API（携程 / 美团开放平台）需要企业资质 + 严格审核，个人 / 个体户通常拿不到。
本服务预留 `query_price()` 接入点：未来具备企业资质并申请到开放平台 key 后，可在其中实现真实比价，
前端无需改动（只要后端返回 prices 字段）。

本服务不依赖外网，离线即可返回结构化渠道列表与深链，保证主流程不崩。
"""
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

# 各渠道元数据。kind: account=官方公众号（复制名称引导微信搜索）/ ota=OTA 平台（复制搜索深链）。
# web 为"搜索该关键词"的网页深链（复制后引导打开）；appId 留空表示暂未配置跨小程序直跳
# （上线后填 navigateToMiniProgramAppIdList 即可升级为直接拉起 App）。
_CHANNELS = {
    "ticket": [
        {"key": "official", "name": "景区官方公众号/小程序", "kind": "account",
         "note": "通常最便宜 · 可直接预约", "recommend": True, "color": "#07C160"},
        {"key": "ctrip", "name": "携程", "kind": "ota", "note": "比价常用 · 退改灵活",
         "color": "#2577E3", "web": "https://www.ctrip.com/search?q={q}"},
        {"key": "meituan", "name": "美团", "kind": "ota", "note": "常有限时折扣",
         "color": "#FFD100", "web": "https://www.meituan.com/search?q={q}"},
        {"key": "fliggy", "name": "飞猪", "kind": "ota", "note": "阿里会员价",
         "color": "#FF6A00", "web": "https://www.fliggy.com/search?q={q}"},
        {"key": "tongcheng", "name": "同程旅行", "kind": "ota", "note": "周边游常用",
         "color": "#0086F6", "web": "https://www.ly.com/search?q={q}"},
        {"key": "douyin", "name": "抖音团购", "kind": "ota", "note": "节假日常更便宜",
         "color": "#161823", "web": "https://www.douyin.com/search/{q}"},
    ],
    "food": [
        {"key": "meituan", "name": "美团", "kind": "ota", "note": "到店套餐/代金券常用",
         "color": "#FFD100", "web": "https://www.meituan.com/search?q={q}"},
        {"key": "dianping", "name": "大众点评", "kind": "ota", "note": "看真实评价+买单优惠",
         "color": "#FF6633", "web": "https://www.dianping.com/search?q={q}"},
        {"key": "douyin", "name": "抖音团购", "kind": "ota", "note": "短视频套餐常更便宜",
         "color": "#161823", "web": "https://www.douyin.com/search/{q}"},
        {"key": "xiaohongshu", "name": "小红书", "kind": "ota", "note": "探店笔记/隐藏优惠",
         "color": "#FF2442", "web": "https://www.xiaohongshu.com/search_result?keyword={q}"},
    ],
    "hotel": [
        {"key": "ctrip", "name": "携程", "kind": "ota", "note": "房源全 · 可订即住",
         "color": "#2577E3", "web": "https://www.ctrip.com/search?q={q}"},
        {"key": "meituan", "name": "美团", "kind": "ota", "note": "钟点房/特价多",
         "color": "#FFD100", "web": "https://www.meituan.com/search?q={q}"},
        {"key": "fliggy", "name": "飞猪", "kind": "ota", "note": "阿里会员价",
         "color": "#FF6A00", "web": "https://www.fliggy.com/search?q={q}"},
        {"key": "tongcheng", "name": "同程旅行", "kind": "ota", "note": "周边住宿常用",
         "color": "#0086F6", "web": "https://www.ly.com/search?q={q}"},
        {"key": "qunar", "name": "去哪儿", "kind": "ota", "note": "低价聚合",
         "color": "#FF7A00", "web": "https://www.qunar.com/search?q={q}"},
    ],
}


class OtaService:
    def list_channels(self, category: str, query: str = "") -> list:
        """返回某品类（ticket/food/hotel）的渠道列表，含按 query 拼好的搜索深链。"""
        base = _CHANNELS.get(category, [])
        q = (query or "").strip()
        out = []
        for c in base:
            item = dict(c)
            if q and item.get("web"):
                item["search"] = item["web"].format(q=quote(q))
            elif item.get("kind") == "account" and q:
                item["value"] = q
            out.append(item)
        return out

    def query_price(self, category: str, query: str, channel: str = None) -> dict:
        """预留：实时票价 / 酒店比价。

        真实实现需企业资质 + 携程 / 美团等开放平台 key（当前不具备）。
        返回 available=False 告知前端继续走「推荐渠道 + 跳转」降级。
        未来接入时，在此发起对开放平台的鉴权请求并解析价格，返回
        {"available": True, "prices": [{channel, price, url}]} 即可，前端无需改动。
        """
        return {
            "available": False,
            "reason": "enterprise_required",
            "message": "实时比价需企业资质并接入 OTA 开放平台，当前以推荐渠道+跳转方式提供。",
            "category": category,
            "query": query,
            "channel": channel,
        }


ota_service = OtaService()

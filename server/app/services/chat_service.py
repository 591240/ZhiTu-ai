from app.ai.llm_client import llm_client
from app.config import settings


def _fake_qa(q: str) -> str:
    t = (q or "")
    if "西湖" in t:
        return "西湖全天免费开放，建议清晨或傍晚前往人少景美；核心景点有断桥、苏堤、雷峰塔（登塔需门票40元）。"
    if "避雷" in t or "坑" in t:
        return "避坑提示：①景区门口拉客的低价团勿信；②网红餐厅排队久可错峰；③打车用平台叫车，别上黑车。"
    if "行李" in t or "打包" in t:
        return "行李清单已生成，请查看下方清单卡片。"
    return "已收到你的问题。作为行程助手，我可以帮你查询目的地美食、景区开放时间、避坑建议和行李清单，请描述更具体的需求。"


def _chunk(text: str):
    """把整段文字按标点切小片，模拟流式输出。"""
    import re
    parts = re.split(r"(?<=[。！？])", text)
    return [p for p in parts if p]


class ChatService:
    async def qa(self, question: str) -> str:
        prompt = f"用户问题：{question}\n请简洁实用地回答旅游相关问题。"
        ans = await llm_client.generate_text(prompt)
        return ans if ans else _fake_qa(question)

    async def qa_stream(self, question: str):
        """流式回答。有 Key 走真 LLM 流式；无 Key 走本地假答案分片。"""
        if settings.llm_api_key:
            async for tok in llm_client.generate_text_stream(
                f"用户问题：{question}\n请简洁实用地回答旅游相关问题。"
            ):
                yield tok
            return
        for piece in _chunk(_fake_qa(question)):
            yield piece

    async def luggage(self) -> dict:
        return {"list": [
            {"group": "衣物", "items": ["外套", "舒适运动鞋", "换洗衣物"]},
            {"group": "洗漱", "items": ["牙刷牙膏", "防晒霜", "护肤品"]},
            {"group": "电子", "items": ["充电宝", "数据线", "耳机"]},
            {"group": "药品", "items": ["创可贴", "肠胃药", "晕车药"]},
        ]}

    async def food(self, city: str) -> dict:
        return {
            "red": [f"{city or '当地'}老字号餐馆", "夜市人气小吃", "景区外居民区餐厅"],
            "black": ["景区内高价套餐", "拉客低价团餐", "无明码标价大排档"],
        }


chat_service = ChatService()

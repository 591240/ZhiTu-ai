"""多轮行程管家 Agent（LangGraph 编排）。

用户用自然语言跟 Agent 聊，Agent 自主决定调用哪些工具、调用几轮：
  - get_trip          只读：查当前行程详情
  - update_trip       受控写：把修改后的完整行程 JSON 落库
  - search_knowledge  只读：Milvus 知识库检索（攻略/POI）

图结构：START → agent ⇄ tools → END（agent 无工具调用时结束）。
写操作收敛为单一工具且强制先读后写，Agent 不能凭空造行程数据。
"""
import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

from app.config import settings
from app.services.trip_service import trip_service
from app.services.chat_service import chat_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是知途旅行的行程管家 Agent，用户会用自然语言让你查询或修改TA的行程。
可用工具：
- get_trip：查看当前行程完整 JSON（包含每天的安排）。
- update_trip：把修改后的行程落库。必须先 get_trip 拿到现有内容，只做用户要求的局部修改，
  其余字段原样保留，再整份提交；不要编造用户没提的改动；一次会话只提交一次。
- search_knowledge：查询旅游知识库（攻略、景点、美食等），不确定的信息先查再答。
回答用简洁中文；修改完成后用一句话告诉用户改了什么。"""


def _build_tools(user_id: int, trip_id: int):
    """工具闭包绑定当前用户与行程，防越权：只允许操作本人行程。"""

    @tool
    async def get_trip() -> str:
        """查看当前行程的完整 JSON 内容。"""
        trip = await trip_service.detail(trip_id, user_id)
        if not trip:
            return json.dumps({"error": "行程不存在或无权访问"}, ensure_ascii=False)
        return json.dumps(trip, ensure_ascii=False)

    @tool
    async def update_trip(content: str) -> str:
        """提交修改后的完整行程 JSON 字符串，落库并返回结果。"""
        try:
            trip = json.loads(content)
        except json.JSONDecodeError:
            return "提交失败：content 不是合法 JSON"
        if not isinstance(trip, dict) or "content" not in trip:
            return "提交失败：缺少 content 字段，请先 get_trip 后原样返回完整结构"
        trip["id"] = trip_id
        try:
            new_id = await trip_service.save(user_id, trip)
        except Exception as e:
            logger.warning("update_trip 落库失败: %s", e)
            return f"落库失败：{e}"
        return f"已保存，行程 id={new_id}"

    @tool
    async def search_knowledge(query: str) -> str:
        """检索旅游知识库，返回相关攻略/景点/美食片段。"""
        res = await chat_service._retrieve_async(query)
        return json.dumps(res.get("hits", [])[:5], ensure_ascii=False)

    return [get_trip, update_trip, search_knowledge]


class TripAgent:
    """按会话构建一次图实例（工具与用户/行程绑定，不跨请求复用）。"""

    def _build(self, user_id: int, trip_id: int):
        tools = _build_tools(user_id, trip_id)
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_url.rstrip("/"),
            timeout=60,
            extra_body={"thinking": {"type": "disabled"}},
        ).bind_tools(tools)
        tool_node = ToolNode(tools)

        async def agent_node(state: MessagesState):
            msgs = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
            return {"messages": [await llm.ainvoke(msgs)]}

        def should_continue(state: MessagesState):
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        g = StateGraph(MessagesState)
        g.add_node("agent", agent_node)
        g.add_node("tools", tool_node)
        g.add_edge(START, "agent")
        g.add_conditional_edges("agent", should_continue, ["tools", END])
        g.add_edge("tools", "agent")
        return g.compile()

    async def run(self, user_id: int, trip_id: int, message: str,
                  history: list[dict] | None = None) -> dict:
        if not settings.llm_api_key:
            raise RuntimeError("LLM 未配置")
        graph = self._build(user_id, trip_id)
        msgs = [HumanMessage(content=h["content"]) if h.get("role") == "user"
                else AIMessage(content=h["content"]) for h in (history or [])]
        msgs.append(HumanMessage(content=message))
        state = await graph.ainvoke(
            {"messages": msgs}, config={"recursion_limit": 15}
        )
        actions, reply = [], ""
        for m in state["messages"]:
            calls = getattr(m, "tool_calls", None)
            if calls:
                actions += [c["name"] for c in calls]
            elif isinstance(m, ToolMessage):
                actions.append(f"{m.name}(done)")
            elif isinstance(m, AIMessage) and m.content:
                reply = m.content if isinstance(m.content, str) else str(m.content)
        return {"reply": reply, "actions": actions}


trip_agent = TripAgent()

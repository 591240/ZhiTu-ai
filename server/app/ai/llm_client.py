"""LLM 封装（LangChain 引擎）。

基于 LangChain 的 ChatOpenAI 统一接入 OpenAI 兼容接口（DeepSeek 等），
对外暴露 generate_json / generate_text / generate_text_stream 三个方法，
调用方（plan_service / chat_service）无需感知底层实现。
未配置 API Key 时返回 None，调用方回退到本地 Mock 生成器。
"""
import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PLANNER = "你是专业旅游行程规划师，只输出JSON格式结果。"
SYSTEM_ASSISTANT = "你是旅游智能助手，回答简洁实用。"


def _extract_text(content) -> str:
    """AIMessage.content 兼容处理：字符串直接返回，列表则拼接 text 片段。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip()
    return str(content)


class LLMClient:
    """LangChain ChatOpenAI 封装。"""

    def _client(self, temperature: float | None = None, json_mode: bool = False) -> ChatOpenAI:
        if not settings.llm_api_url:
            raise RuntimeError("LLM_API_URL 未配置")
        # thinking 是 DeepSeek 私有字段，openai SDK 新版拒绝未知顶层参数，
        # 必须经 extra_body 注入请求体；response_format 是标准字段可直接透传
        extra_body = {"thinking": self._thinking_field()}
        model_kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_url.rstrip("/"),
            temperature=temperature if temperature is not None else 0.7,
            timeout=60,
            extra_body=extra_body,
            model_kwargs=model_kwargs,
        )

    def _thinking_field(self):
        # 思考模式开关：开启则限制预算避免无限推理，关闭则彻底省 token
        if settings.llm_thinking:
            return {"type": "enabled", "budget_tokens": 4096}
        return {"type": "disabled"}

    async def generate_json(self, prompt: str, temperature: float = 0.7):
        if not settings.llm_api_key:
            return None
        llm = self._client(temperature=temperature, json_mode=True)
        msg = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PLANNER),
            HumanMessage(content=prompt),
        ])
        content = _extract_text(msg.content)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            m = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if m:
                return json.loads(m.group(1))
            raise Exception("LLM 返回格式异常")

    async def generate_tool_call(self, system: str, prompt: str,
                                 tools: list[dict], temperature: float = 0.2):
        """Function Calling：让模型调用工具，返回第一个工具调用的参数 dict。

        tools 为 OpenAI 工具 schema 列表；模型没有发起工具调用时返回 None，
        由调用方决定回退策略。单轮调用，不处理工具结果回传。
        """
        if not settings.llm_api_key:
            return None
        llm = self._client(temperature=temperature).bind_tools(tools)
        msg = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ])
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            return None
        return calls[0].get("args") or {}

    async def generate_text(self, prompt: str):
        if not settings.llm_api_key:
            return None
        llm = self._client()
        msg = await llm.ainvoke([
            SystemMessage(content=SYSTEM_ASSISTANT),
            HumanMessage(content=prompt),
        ])
        return _extract_text(msg.content)

    async def generate_text_stream(self, prompt: str):
        """流式生成文本（SSE）。无 Key 时不产出任何 token（调用方走降级）。"""
        if not settings.llm_api_key:
            return
        llm = self._client()
        async for chunk in llm.astream([
            SystemMessage(content=SYSTEM_ASSISTANT),
            HumanMessage(content=prompt),
        ]):
            delta = _extract_text(chunk.content)
            if delta:
                yield delta


llm_client = LLMClient()

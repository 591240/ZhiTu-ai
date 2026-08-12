import json
import re

import httpx

from app.config import settings


class LLMClient:
    """LLM 封装。未配置 API Key 时返回 None，调用方回退到本地 Mock 生成器。"""

    def _thinking_field(self):
        # 思考模式开关：开启则限制预算避免无限推理，关闭则彻底省 token
        if settings.llm_thinking:
            return {"type": "enabled", "budget_tokens": 4096}
        return {"type": "disabled"}

    async def generate_json(self, prompt: str, temperature: float = 0.7):
        if not settings.llm_api_key:
            return None
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.llm_api_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": "你是专业旅游行程规划师，只输出JSON格式结果。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                    "thinking": self._thinking_field(),
                },
            )
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                m = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
                if m:
                    return json.loads(m.group(1))
                raise Exception("LLM 返回格式异常")

    async def generate_text(self, prompt: str):
        if not settings.llm_api_key:
            return None
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.llm_api_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": "你是旅游智能助手，回答简洁实用。"},
                        {"role": "user", "content": prompt},
                    ],
                    "thinking": self._thinking_field(),
                },
            )
            return resp.json()["choices"][0]["message"]["content"]

    async def generate_text_stream(self, prompt: str):
        """流式生成文本（SSE）。无 Key 时不产出任何 token（调用方走降级）。"""
        if not settings.llm_api_key:
            return
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_api_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": "你是旅游智能助手，回答简洁实用。"},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": True,
                    "thinking": self._thinking_field(),
                },
            ) as resp:
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue


llm_client = LLMClient()

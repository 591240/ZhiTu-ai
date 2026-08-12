"""视觉多模态客户端（识图 / 识别视频）。

与 llm_client 保持同一套 OpenAI 兼容协议，只是消息里带 image_url 内容块。
当前行程生成的 DeepSeek 是纯文本模型，无法处理图片/视频，因此识别功能单独走这里。

接入方式：在 .env 填 vision_api_key / vision_api_url / vision_model 即可。
未配置 key 时 analyze() 返回 None，由调用方回退到示例数据（保证链路可跑）。
"""
import base64
import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger("vision_client")


class VisionClient:
    async def analyze(self, images: list[bytes], prompt: str) -> dict | None:
        """多图（图片直接一张；视频抽帧传多张）送入视觉模型，返回解析后的 JSON dict。

        返回 None 表示未配置 key 或调用失败，调用方应回退示例。
        兼容策略：优先带 response_format=json_object 请求；若服务端报 400/422，
        则降级为不带 response_format 的普通请求，依靠 prompt 强制 JSON。
        """
        if not settings.vision_api_key:
            return None
        if not images:
            return None

        content = [{"type": "text", "text": prompt}]
        for img in images:
            b64 = base64.b64encode(img).decode("utf-8")
            # 用 data URI 传入；模型按服务商支持自动识别图片
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            )

        async with httpx.AsyncClient(timeout=90) as client:
            # 第一次：尝试 JSON 模式
            try:
                resp = await client.post(
                    f"{settings.vision_api_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.vision_api_key}"},
                    json={
                        "model": settings.vision_model,
                        "messages": [{"role": "user", "content": content}],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
                parsed = _extract_json(text)
                if parsed:
                    return parsed
                logger.warning("视觉模型返回非 JSON，尝试第二次请求: %s", text[:200])
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                logger.warning("视觉模型 JSON 模式请求失败，状态码=%s，尝试降级", status)
                # 400/422 通常表示 response_format 不被支持，降级重试
                if status not in (400, 422):
                    logger.exception("视觉模型调用失败，回退示例数据")
                    return None
            except Exception:
                logger.exception("视觉模型调用失败，回退示例数据")
                return None

            # 第二次：不带 response_format，靠 prompt 约束 JSON
            try:
                resp = await client.post(
                    f"{settings.vision_api_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.vision_api_key}"},
                    json={
                        "model": settings.vision_model,
                        "messages": [{"role": "user", "content": content}],
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
                return _extract_json(text)
            except Exception:
                logger.exception("视觉模型降级调用失败，回退示例数据")
                return None


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        import re

        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


vision_client = VisionClient()

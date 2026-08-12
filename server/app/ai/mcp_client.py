"""通用 MCP streamable-HTTP 客户端。

复用于：高德地图 MCP（geocode）、后续其它 MCP（如景点发现）等。
协议：每次调用独立完成 initialize → initialized → tools/call 握手，不缓存 session，
避免并发串号。任何异常向上抛出，由调用方决定降级策略。
"""
import json
import logging

import httpx

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"
TIMEOUT = 20


def _parse_response(r: httpx.Response):
    ct = r.headers.get("content-type", "")
    text = r.text or ""
    if "text/event-stream" in ct:
        for line in reversed(text.splitlines()):
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                try:
                    return json.loads(chunk)
                except Exception:
                    continue
        return None
    try:
        return r.json()
    except Exception:
        return None


def _extract_text(resp) -> str | None:
    if not resp:
        return None
    result = resp.get("result")
    if not result:
        return None
    content = result.get("content")
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        return "\n".join(p for p in parts if p).strip() or None
    if isinstance(result, dict):
        return result.get("text") or result.get("content")
    return None


async def call_mcp_tool(url: str, tool_name: str, arguments: dict, timeout: int = TIMEOUT) -> str | None:
    """调用 MCP 工具并返回其 text 结果；失败抛异常。"""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "zhitu-backend", "version": "1.0.0"},
            },
        }, headers=headers, timeout=timeout)
        sid = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id")
        if sid:
            headers["Mcp-Session-Id"] = sid
        await client.post(url, json={
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {}
        }, headers=headers, timeout=timeout)
        r2 = await client.post(url, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }, headers=headers, timeout=timeout)
        return _extract_text(_parse_response(r2))

import json
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TIMEOUT = 20
# MCP streamable HTTP 稳定协议版本（12306-mcp 基于 modelcontextprotocol/typescript-sdk）
PROTOCOL_VERSION = "2024-11-05"

_FALLBACK_HINT = (
    "（当前为离线估算，未接入实时票务。在服务器启动 12306-mcp 并把 "
    "TICKET_MCP_URL 指向它后，即可查询真实余票/票价。）"
)


class TicketService:
    """查询 12306 真实余票/车次。

    通过 MCP 协议调用本地 12306-mcp 服务（Node 进程，HTTP 模式）。
    任何异常（未配置 / 连不上 / 超时 / 解析失败）都会降级为离线估算提示，
    保证主流程不崩。

    每次查询都独立完成 initialize → initialized → tools/call 握手，
    不缓存跨请求的 session，避免并发串号。
    """

    # ---- MCP 底层通信 ----
    async def _post(self, client: httpx.AsyncClient, payload: dict, session_id: str | None = None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        r = await client.post(settings.ticket_mcp_url, json=payload, headers=headers, timeout=TIMEOUT)
        sid = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id")
        return self._parse_response(r), sid

    @staticmethod
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

    async def _ensure_session(self, client: httpx.AsyncClient):
        resp, sid = await self._post(client, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "zhitu-backend", "version": "1.0.0"},
            },
        })
        await self._post(client, {
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
        }, sid)
        return sid

    # ---- 对外查询 ----
    async def search(self, date: str, from_station: str, to_station: str, train_type: str = None) -> dict:
        url = settings.ticket_mcp_url
        if not url:
            return self._fallback(date, from_station, to_station)

        try:
            async with httpx.AsyncClient() as client:
                sid = await self._ensure_session(client)
                args = {"date": date, "fromStation": from_station, "toStation": to_station}
                if train_type:
                    args["trainTypeFilters"] = [train_type]
                resp, _ = await self._post(client, {
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "get-tickets", "arguments": args},
                }, sid)
                raw = self._extract_text(resp)
                if not raw:
                    return self._fallback(date, from_station, to_station)
                return {
                    "source": "12306-mcp",
                    "raw": raw,
                    "trains": self._parse_trains(raw),
                    "date": date,
                    "from": from_station,
                    "to": to_station,
                }
        except Exception as e:
            logger.warning("ticket MCP 查询失败，降级估算：%s", e)
            return self._fallback(date, from_station, to_station)

    @staticmethod
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

    @staticmethod
    def _parse_trains(text: str) -> list:
        """解析 12306-mcp 返回文本，尽力结构化。

        保留前端依赖的 trainNo / line 字段，并尽力补 depart/arrive/prices，
        解析不到的字段留空，不影响展示（前端用 line 兜底显示原文）。

        常见返回形如： "G7503 杭州东 06:00 上海虹桥 07:58 二等座 ¥73 ..."，
        不同 mcp 实现格式略有差异，故全部为尽力而为。
        """
        trains = []
        for line in text.splitlines():
            m = re.match(r"^\s*([GDCKTZ]\d{1,4})", line)
            if not m:
                continue
            train_no = m.group(1)
            times = re.findall(r"\b(\d{1,2}:\d{2})\b", line)
            depart = times[0] if len(times) > 0 else None
            arrive = times[1] if len(times) > 1 else None
            # 时长（如 1小时58分 / 1:58）
            duration = None
            dm = re.search(r"(\d+)\s*小时\s*(\d+)\s*分", line)
            if dm:
                duration = f"{dm.group(1)}h{dm.group(2)}m"
            else:
                dm2 = re.search(r"\b(\d{1,2}):(\d{2})\b", line)
                if dm2 and len(times) >= 2:
                    duration = f"{dm2.group(1)}h{dm2.group(2)}m"
            prices = re.findall(r"¥\s*(\d+(?:\.\d+)?)", line)
            trains.append({
                "trainNo": train_no,
                "line": line.strip(),
                "depart": depart,
                "arrive": arrive,
                "duration": duration,
                "prices": prices,
            })
        return trains[:20]

    @staticmethod
    def _fallback(date: str, frm: str, to: str) -> dict:
        return {
            "source": "fallback",
            "raw": f"从 {frm} 到 {to}（{date}）的实时余票需接入 12306-mcp。{_FALLBACK_HINT}",
            "trains": [],
            "date": date,
            "from": frm,
            "to": to,
        }


ticket_service = TicketService()

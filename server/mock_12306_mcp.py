"""开发期 mock：最小 MCP streamable HTTP 服务，模拟 12306-mcp 的 get-tickets。

用途：沙箱无外网、无法下载/启动真正的 12306-mcp 时，用来验证
app/services/ticket_service.py 的 MCP 握手与调用协议是否正确。
生产环境请改用真实的 12306-mcp（npx -y 12306-mcp --port 8801）。

启动：python mock_12306_mcp.py   （默认 http://127.0.0.1:8901/mcp）
"""
import json

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="mock-12306-mcp")


def _build_fake(args: dict) -> str:
    f = args.get("fromStation", "杭州")
    t = args.get("toStation", "上海")
    d = args.get("date", "")
    return (
        f"【{d} {f} → {t} 余票查询结果（演示数据）】\n"
        f"车次   出发 到达 历时   二等座  一等座  商务座 无座\n"
        f"G7503  {f} {t} 07:25 08:18 00:53  有票¥73 有票¥123 有票¥230 有票¥73\n"
        f"G7505  {f} {t} 08:10 09:05 00:55  有票¥73 有票¥123 有票¥230 有票¥73\n"
        f"D3125  {f} {t} 09:30 10:40 01:10  有票¥45 有票¥72  --     有票¥45\n"
        f"K101   {f} {t} 22:00 06:30 08:30  有票¥38  --      --     有票¥38"
    )


def _dispatch(payload: dict):
    mid = payload.get("id")
    method = payload.get("method")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": mid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "mock-12306", "version": "1.0.0"},
            },
        }
    if method == "notifications/initialized":
        return None  # notification：不返回 JSON-RPC 响应
    if method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": mid,
            "result": {
                "tools": [
                    {"name": "get-tickets", "description": "查询 12306 余票", "inputSchema": {}},
                    {"name": "get-train-route-stations", "description": "经停站", "inputSchema": {}},
                ]
            },
        }
    if method == "tools/call":
        name = payload.get("params", {}).get("name")
        args = payload.get("params", {}).get("arguments", {})
        if name == "get-tickets":
            text = _build_fake(args)
        else:
            text = f"mock: {name} 未实现"
        return {
            "jsonrpc": "2.0", "id": mid,
            "result": {"content": [{"type": "text", "text": text}]},
        }
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}


@app.post("/mcp")
async def mcp(req: Request):
    body = await req.json()
    if isinstance(body, list):
        results = [r for p in body if (r := _dispatch(p)) is not None]
        if not results:
            return Response(status_code=202)
        return JSONResponse(results)
    r = _dispatch(body)
    if r is None:
        return Response(status_code=202)
    resp = JSONResponse(r)
    resp.headers["Mcp-Session-Id"] = "mock-session-001"
    return resp


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8901)

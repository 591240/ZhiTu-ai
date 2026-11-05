import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas import ChatQAReq, LuggageReq, FoodReq, AgentChatReq, ok, fail
from app.deps import get_current_user
from app.services.chat_service import chat_service
from app.services.points_service import points_service
from app.ai.trip_agent import trip_agent
from app.config import settings

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/qa")
async def qa(req: ChatQAReq, user=Depends(get_current_user)):
    """流式问答（SSE）。每片 data: {"text": "..."}，结束 data: {"done": true}。"""
    # 个人主体（变现关闭）不扣积分、不拦截
    if settings.monetization_enabled and not await points_service.consume_chat(user["user_id"]):
        return fail("积分不足，请充值后再提问", code=4001)

    async def event_stream():
        try:
            async for token in chat_service.qa_stream(req.question):
                yield f"data: {json.dumps({'text': token}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/agent")
async def agent_chat(req: AgentChatReq, user=Depends(get_current_user)):
    """多轮行程管家（LangGraph）：Agent 自主调用查/改/检索工具后返回结果。"""
    try:
        return ok(await trip_agent.run(user["user_id"], req.trip_id, req.message, req.history))
    except RuntimeError as e:
        return fail(str(e), code=4002)
    except Exception as e:
        return fail(f"Agent 处理失败：{e}", code=5000)


@router.get("/rag_stats")
async def rag_stats(user=Depends(get_current_user)):
    """RAG 可观测性：提问数、有依据率、无依据拒答率、检索索引状态。"""
    return ok(chat_service.rag_stats())


@router.post("/luggage")
async def luggage(req: LuggageReq, user=Depends(get_current_user)):
    return ok(await chat_service.luggage(req.city, req.days, req.season))


@router.post("/food")
async def food(req: FoodReq, user=Depends(get_current_user)):
    return ok(await chat_service.food(req.city))

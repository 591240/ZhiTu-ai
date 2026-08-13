import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas import ChatQAReq, LuggageReq, FoodReq, ok, fail
from app.deps import get_current_user
from app.services.chat_service import chat_service
from app.services.points_service import points_service
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


@router.post("/luggage")
async def luggage(req: LuggageReq, user=Depends(get_current_user)):
    return ok(await chat_service.luggage())


@router.post("/food")
async def food(req: FoodReq, user=Depends(get_current_user)):
    return ok(await chat_service.food(req.city))

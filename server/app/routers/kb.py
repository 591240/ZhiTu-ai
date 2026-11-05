"""检索接口的只读入口：用来看召回质量，不参与行程生成链路。

生成链路（form / quick / adjust 与 /api/chat/qa）已经接了 RAG——候选景点池见
`kb/candidates.py`，问答的「先检索、检索为空即拒答」在 chat 路由里。
这两个接口负责把「问了会召回什么」暴露出来，召回不靠谱还有得调。
"""
from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.schemas import fail, ok
from kb.retriever import retriever

router = APIRouter(prefix="/api/kb", tags=["kb"])


@router.get("/status")
async def status(user=Depends(get_current_user)):
    from kb import candidates

    data = retriever.status()
    data["candidates"] = dict(candidates.STATS)
    return ok(data)


@router.get("/search")
async def search(
    q: str = Query(..., description="自然语言问题或景点名"),
    city: str = Query(None, description="按城市硬过滤，防止跨城语义串味"),
    top_k: int = Query(5, ge=1, le=20),
    user=Depends(get_current_user),
):
    if not q.strip():
        return fail("q 不能为空")
    return ok(retriever.search(q, city=city, top_k=top_k))

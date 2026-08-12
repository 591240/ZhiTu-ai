import base64

from fastapi import APIRouter, Depends

from app.schemas import ok
from app.deps import get_current_user
from app.services.ocr_service import ocr_service

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/recognize")
async def recognize(body: dict, user=Depends(get_current_user)):
    """识图 / 识别视频。

    前端以 JSON 提交：{ file_base64, filename, mode }
    - mode=itinerary：行程截图 → 城市/天数/景点 → 生成行程
    - mode=scene：风景照/视频 → 识别地点 + 推荐景点
    视频自动按扩展名识别，抽帧后送入视觉模型。
    （采用 base64 JSON 而非 multipart，避免额外依赖 python-multipart。）
    """
    mode = body.get("mode", "itinerary")
    if mode not in ("itinerary", "scene"):
        mode = "itinerary"
    file_b64 = body.get("file_base64", "") or ""
    filename = body.get("filename", "image.jpg") or "image.jpg"
    try:
        data = base64.b64decode(file_b64)
    except Exception:
        data = b""
    result = await ocr_service.recognize(data, filename, mode)
    return ok(result)

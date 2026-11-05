import base64
import binascii

from fastapi import APIRouter, Depends

from app.schemas import ok, fail
from app.deps import get_current_user
from app.services.ocr_service import ocr_service

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

# base64 上限 8MB（原始约 6MB）。视频 base64 轻易几十 MB，
# 不设限的话单个请求就能把 2GB 机器的内存吃满。
MAX_B64_CHARS = 8 * 1024 * 1024


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

    if not file_b64:
        return fail("未收到文件内容", code=400)
    if len(file_b64) > MAX_B64_CHARS:
        return fail("文件过大，请压缩到 6MB 以内再上传", code=413)
    try:
        data = base64.b64decode(file_b64, validate=False)
    except (binascii.Error, ValueError):
        return fail("文件内容不是合法的 base64", code=400)
    if not data:
        return fail("文件内容为空", code=400)

    result = await ocr_service.recognize(data, filename, mode)
    return ok(result)

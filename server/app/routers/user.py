from datetime import datetime

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import select, func

from app.schemas import ok, fail, UserProfileReq, FeedbackReq, RechargeReq
from app.deps import get_current_user
from app.database import SessionLocal
from app.models import Trip, User, Feedback
from app.config import settings, BASE_DIR
from app.utils.wechat import check_text_security

router = APIRouter(prefix="/api/user", tags=["user"])


def _user_dict(user: User):
    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar": user.avatar or "",
        "phone": user.phone or "",
        "city": user.city,
        "is_vip": user.is_vip,
        "points": user.points,
    }


@router.get("/me")
async def me(user=Depends(get_current_user)):
    """返回当前登录用户完整信息。"""
    async with SessionLocal() as s:
        u = (
            await s.execute(select(User).where(User.id == user["user_id"], User.is_active == True))
        ).scalar_one_or_none()
        if not u:
            return fail("用户不存在或已注销", code=401)
        return ok(_user_dict(u))


@router.post("/profile")
async def update_profile(req: UserProfileReq, user=Depends(get_current_user)):
    """更新当前用户头像/昵称。"""
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.id == user["user_id"]))).scalar_one_or_none()
        if not u:
            return fail("用户不存在", code=404)
        if req.nickname is not None:
            new_nick = req.nickname.strip()
            if new_nick and new_nick != (u.nickname or ""):
                passed, reason = await check_text_security(
                    new_nick, user.get("openid", ""), scene=1, title="昵称"
                )
                if not passed:
                    return fail(reason)
            u.nickname = new_nick or u.nickname
        if req.avatar is not None:
            u.avatar = req.avatar.strip()
        await s.commit()
        await s.refresh(u)
        return ok(_user_dict(u))


MAX_AVATAR_BYTES = 5 * 1024 * 1024

# 文件魔数 → 扩展名。content_type 是客户端随便填的，只能作为第一道粗筛，
# 真正决定落盘类型的是文件头。
_MAGIC = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
)


def _sniff_image_ext(head: bytes) -> str | None:
    for magic, ext in _MAGIC:
        if head.startswith(magic):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


@router.post("/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...), user=Depends(get_current_user)):
    """上传头像并返回永久可访问 URL。"""
    allowed_content_types = {"image/jpeg", "image/png", "image/jpg", "image/gif", "image/webp"}
    if file.content_type not in allowed_content_types:
        return fail("仅支持 jpg/png/gif/webp 图片", code=400)

    data = await file.read(MAX_AVATAR_BYTES + 1)
    await file.close()
    if len(data) > MAX_AVATAR_BYTES:
        return fail("头像不能超过 5MB", code=413)

    ext = _sniff_image_ext(data[:16])
    if not ext:
        return fail("文件内容不是有效的图片", code=400)

    avatar_dir = BASE_DIR / "static" / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"u{user['user_id']}_{ts}{ext}"
    filepath = avatar_dir / filename

    try:
        with open(filepath, "wb") as f:
            f.write(data)
    except Exception as e:
        return fail(f"保存头像失败: {e}", code=500)

    # 生成永久 URL：优先用显式配置，否则从请求头推导（网关会传 Host 与 X-Forwarded-Proto）
    base_url = (settings.public_base_url or "").rstrip("/")
    if not base_url:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
        if host:
            scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
            base_url = f"{scheme}://{host}"
    url = f"{base_url}/static/avatars/{filename}"

    # 同步写入用户表，并删掉旧头像文件（否则磁盘只增不减）
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.id == user["user_id"]))).scalar_one_or_none()
        if u:
            old = u.avatar or ""
            u.avatar = url
            await s.commit()
            await s.refresh(u)
            if "/static/avatars/" in old:
                old_path = avatar_dir / old.rsplit("/static/avatars/", 1)[-1]
                if old_path.name != filename and old_path.parent == avatar_dir:
                    try:
                        old_path.unlink(missing_ok=True)
                    except OSError:
                        pass
            return ok(_user_dict(u))
    return ok({"avatar": url})


@router.post("/feedback")
async def submit_feedback(req: FeedbackReq, user=Depends(get_current_user)):
    """提交意见反馈。"""
    if not req.content or not req.content.strip():
        return fail("反馈内容不能为空")
    passed, reason = await check_text_security(req.content, user.get("openid", ""), scene=2)
    if not passed:
        return fail(reason)
    async with SessionLocal() as s:
        fb = Feedback(
            user_id=user["user_id"],
            content=req.content.strip(),
            contact=(req.contact or "").strip(),
        )
        s.add(fb)
        await s.commit()
    return ok("反馈已收到")


@router.post("/deactivate")
async def deactivate(user=Depends(get_current_user)):
    """注销当前账号（软删除，标记 is_active=False）。"""
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.id == user["user_id"]))).scalar_one_or_none()
        if not u:
            return fail("用户不存在", code=404)
        u.is_active = False
        # 可选：清空敏感信息
        u.phone = ""
        await s.commit()
    return ok("账号已注销")


@router.get("/stats")
async def stats(user=Depends(get_current_user)):
    """返回当前用户的行程数、去过的城市数（个人中心展示）。"""
    async with SessionLocal() as s:
        trip_count = (
            await s.execute(
                select(func.count())
                .select_from(Trip)
                .where(Trip.user_id == user["user_id"], Trip.status != "deleted")
            )
        ).scalar() or 0
        city_count = (
            await s.execute(
                select(func.count(func.distinct(Trip.city)))
                .select_from(Trip)
                .where(Trip.user_id == user["user_id"], Trip.status != "deleted")
            )
        ).scalar() or 0
    return ok({"tripCount": trip_count, "cityCount": city_count})


@router.get("/points")
async def get_points(user=Depends(get_current_user)):
    """查询当前用户积分余额。"""
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.id == user["user_id"]))).scalar_one_or_none()
        if not u:
            return fail("用户不存在", code=404)
        return ok({"points": u.points})


@router.post("/recharge")
async def recharge(req: RechargeReq, user=Depends(get_current_user)):
    """人工充值申请：记录金额和联系方式，由管理员线下确认后加积分。"""
    if req.amount <= 0:
        return fail("充值金额必须大于 0")
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.id == user["user_id"]))).scalar_one_or_none()
        if not u:
            return fail("用户不存在", code=404)
        # 这里只记录申请，实际加积分由管理员后台/手动完成
        # 简单起见，先把申请写入 feedback 表作为待办通知
        fb = Feedback(
            user_id=u.id,
            content=f"[充值申请] 金额 ¥{req.amount}，联系方式：{req.contact}，备注：{req.note}",
            contact=req.contact,
        )
        s.add(fb)
        await s.commit()
    # message 放平到顶层：嵌在 data 里的话前端 request 层拿不到，
    # 会被统一盖成"请求失败"（实际申请已经写进反馈表了）。
    return ok(None, message="充值申请已提交，请扫码支付后联系客服加积分")

from fastapi import APIRouter, Depends
from sqlalchemy import select, func

from app.schemas import ok, fail, UserProfileReq, FeedbackReq, RechargeReq
from app.deps import get_current_user
from app.database import SessionLocal
from app.models import Trip, User, Feedback

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
            u.nickname = req.nickname.strip() or u.nickname
        if req.avatar is not None:
            u.avatar = req.avatar.strip()
        await s.commit()
        await s.refresh(u)
        return ok(_user_dict(u))


@router.post("/feedback")
async def submit_feedback(req: FeedbackReq, user=Depends(get_current_user)):
    """提交意见反馈。"""
    if not req.content or not req.content.strip():
        return fail("反馈内容不能为空")
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
    return ok({"message": "充值申请已提交，请扫码支付后联系客服加积分"})

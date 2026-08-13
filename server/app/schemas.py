from typing import Optional, Any, List

from pydantic import BaseModel


class LoginReq(BaseModel):
    code: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    phone_code: Optional[str] = None   # 微信手机号快速验证回调返回的 code


class UserOut(BaseModel):
    id: int
    nickname: str
    avatar: str = ""
    phone: str = ""
    city: str = "杭州"
    is_vip: bool = False


class BindPhoneReq(BaseModel):
    phone_code: str


class UserProfileReq(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class FeedbackReq(BaseModel):
    content: str
    contact: Optional[str] = ""


class SmsSendReq(BaseModel):
    phone: str


class PhoneLoginReq(BaseModel):
    phone: str
    code: str


class TokenOut(BaseModel):
    token: str
    user: UserOut


class PlanFormReq(BaseModel):
    city: str
    days: int = 2
    crowd_type: str = "朋友"
    budget_min: int = 500          # 自定义预算下限（元/人）
    budget_max: int = 1500         # 自定义预算上限（元/人）
    preferences: List[str] = []
    transport_mode: str = "地铁"          # 市内交通方式
    route_type: str = "popular"
    remark: str = ""
    # —— 新增维度（文档 3.1 节：往返交通 / 时间 / 人数）——
    departure_city: str = ""             # 出发城市（往返交通方案起点）
    start_date: str = ""                 # 出发日期 YYYY-MM-DD（用于季节/天气适配）
    end_date: str = ""                   # 返程日期 YYYY-MM-DD
    people_count: int = 2                # 出行人数
    transport_preference: str = ""       # 往返交通偏好：高铁优先/飞机优先/性价比优先/省时优先


class PlanQuickReq(BaseModel):
    text: str


class TripSaveReq(BaseModel):
    trip: dict


class AdjustReq(BaseModel):
    trip: dict
    instruction: str


class ChatQAReq(BaseModel):
    question: str


class RechargeReq(BaseModel):
    amount: float                 # 充值金额
    contact: str = ""             # 微信号/手机号，用于人工确认
    note: str = ""                # 备注


class LuggageReq(BaseModel):
    city: str = ""
    days: int = 2
    season: str = ""


class FoodReq(BaseModel):
    city: str


def ok(data: Any = None, message: str = "ok"):
    return {"code": 0, "data": data, "message": message}


def fail(message: str = "error", code: int = 1):
    return {"code": code, "data": None, "message": message}

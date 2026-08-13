from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, JSON, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(64), default="微信用户")
    avatar: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", nullable=True)
    city: Mapped[str] = mapped_column(String(32), default="杭州")
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    vip_expire_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=100)  # 积分余额
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=True)
    invited_by: Mapped[int] = mapped_column(Integer, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DistributionRecord(Base):
    """分销佣金记录：被邀请人产生付费/注册行为时，记录邀请人应得佣金。"""
    __tablename__ = "distribution_records"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    distributor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # 邀请人
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)    # 被邀请人
    ref_type: Mapped[str] = mapped_column(String(16), default="order")  # register / order
    ref_id: Mapped[int] = mapped_column(Integer, default=0)              # 关联订单/行程 id
    amount: Mapped[float] = mapped_column(Float, default=0)             # 计费基数（订单金额）
    commission: Mapped[float] = mapped_column(Float, default=0)         # 佣金金额
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / settled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Event(Base):
    """数据埋点事件表。"""
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    props: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    contact: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    city: Mapped[str] = mapped_column(String(32))
    days: Mapped[int] = mapped_column(Integer, default=1)
    route_type: Mapped[str] = mapped_column(String(16), default="popular")
    crowd_type: Mapped[str] = mapped_column(String(16), default="朋友")
    budget_level: Mapped[str] = mapped_column(String(16), default="舒适")
    total_budget: Mapped[float] = mapped_column(Float, default=0)
    content: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128))
    city: Mapped[str] = mapped_column(String(32), index=True)
    days: Mapped[int] = mapped_column(Integer, default=1)
    spots_count: Mapped[int] = mapped_column(Integer, default=0)
    route_type: Mapped[str] = mapped_column(String(16), default="popular")
    cover: Mapped[str] = mapped_column(String(32), default="")
    content: Mapped[dict] = mapped_column(JSON)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Collection(Base):
    __tablename__ = "collections"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True)
    plan_type: Mapped[str] = mapped_column(String(16))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class City(Base):
    __tablename__ = "cities"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), index=True)
    province: Mapped[str] = mapped_column(String(32), default="")
    pinyin: Mapped[str] = mapped_column(String(32), default="")
    is_hot: Mapped[bool] = mapped_column(Boolean, default=False)


class ServiceLink(Base):
    __tablename__ = "service_links"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32))
    app_id: Mapped[str] = mapped_column(String(64), default="")
    path: Mapped[str] = mapped_column(String(128), default="")
    icon: Mapped[str] = mapped_column(String(32), default="")


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

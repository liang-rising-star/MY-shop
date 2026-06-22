"""
抽奖系统数据库模型
"""
import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class LotteryWheel(Base):
    """抽奖转盘"""
    __tablename__ = "lottery_wheels"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    image_url = Column(String(500), default="")
    price_type = Column(String(20), default="points")  # points积分, ticket抽奖券, free免费
    price_value = Column(Integer, default=10)  # 价格：积分数/抽奖券数
    free_daily = Column(Integer, default=0)  # 每日免费次数
    min_points = Column(Integer, default=0)  # 最少积分要求
    max_daily = Column(Integer, default=0)  # 每日最多抽奖次数（0不限制）
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LotteryPrize(Base):
    """抽奖奖品"""
    __tablename__ = "lottery_prizes"
    id = Column(Integer, primary_key=True)
    wheel_id = Column(Integer, ForeignKey("lottery_wheels.id"), nullable=False)
    name = Column(String(100), nullable=False)
    prize_type = Column(String(50), nullable=False)  # coupon优惠券, ticket抽奖券, product商品, points积分
    prize_value = Column(Text, default="")  # 奖品值：优惠券ID/积分数量/商品信息
    probability = Column(Float, default=0)  # 中奖概率（百分比）
    is_default = Column(Boolean, default=False)  # 是否是默认奖品（保底）
    stock = Column(Integer, default=-1)  # 库存，-1表示无限
    total_stock = Column(Integer, default=0)  # 总库存
    sort_order = Column(Integer, default=0)
    image_url = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LotteryRecord(Base):
    """抽奖记录"""
    __tablename__ = "lottery_records"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    wheel_id = Column(Integer, ForeignKey("lottery_wheels.id"), nullable=False)
    prize_id = Column(Integer, ForeignKey("lottery_prizes.id"), nullable=False)
    cost_type = Column(String(20), default="points")  # points积分, ticket抽奖券, free免费
    cost_value = Column(Integer, default=0)  # 消耗数量
    ip_address = Column(String(50), default="")
    is_winner = Column(Boolean, default=False)
    status = Column(String(20), default="pending")  # pending待领取, claimed已领取, expired已过期
    prize_data = Column(Text, default="")  # 奖品详情JSON
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LotteryTicket(Base):
    """抽奖券"""
    __tablename__ = "lottery_tickets"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    wheel_id = Column(Integer, ForeignKey("lottery_wheels.id"), nullable=True)
    status = Column(String(20), default="active")  # active可用, used已使用, expired已过期
    expires_at = Column(DateTime, nullable=True)
    source = Column(String(50), default="")  # 获取来源：purchase购买, coupon优惠券兑换, admin管理员发放
    order_id = Column(Integer, nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

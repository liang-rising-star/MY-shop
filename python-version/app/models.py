import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    email = Column(String(100), default="")
    phone = Column(String(20), default="")
    avatar = Column(String(500), default="")
    real_name = Column(String(50), default="")
    level = Column(Integer, default=0)
    points = Column(Integer, default=0)
    balance = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    total_commission = Column(Float, default=0.0)
    total_recharge = Column(Float, default=0.0)
    invite_code = Column(String(20), unique=True, nullable=True)
    invite_uid = Column(Integer, nullable=True)
    team_count = Column(Integer, default=0)
    login_ip = Column(String(50), default="")
    last_login_ip = Column(String(50), default="")
    login_time = Column(DateTime, nullable=True)
    last_login_time = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)
    admin_permissions = Column(Text, default="")
    status = Column(String(20), default="normal")
    alipay_account = Column(String(100), default="")
    wechat_account = Column(String(100), default="")
    wallet_address = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ProductCategory(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    short_description = Column(String(500), default="")
    description = Column(Text, default="")
    content = Column(Text, default="")
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    cost_price = Column(Float, nullable=True)
    discount = Column(Float, default=0)
    discount_mode = Column(String(20), default="none")
    discount_percent = Column(Float, default=0)
    discount_price = Column(Float, nullable=True)
    discount_start = Column(DateTime, nullable=True)
    discount_end = Column(DateTime, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), default=0)
    image_url = Column(String(500), default="")
    images = Column(Text, default="")
    video_url = Column(String(500), default="")
    featured = Column(Boolean, default=False)
    is_hot = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)
    is_recommend = Column(Boolean, default=False)
    is_seckill = Column(Boolean, default=False)
    type = Column(String(20), default="normal")
    stock = Column(Integer, default=-1)
    stock_warning = Column(Integer, default=10)
    max_buy_limit = Column(Integer, default=0)
    per_user_limit = Column(Integer, default=0)
    total_sold = Column(Integer, default=0)
    delivery_type = Column(String(20), default="card_key")
    file_path = Column(String(500), default="")
    file_name = Column(String(200), default="")
    file_size = Column(String(50), default="")
    files_list = Column(Text, default="")
    auto_delivery_content = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    seo_title = Column(String(200), default="")
    seo_keywords = Column(String(500), default="")
    seo_description = Column(String(1000), default="")
    tags = Column(String(500), default="")
    buy_notice = Column(Text, default="")
    after_sale_notice = Column(Text, default="")
    view_count = Column(Integer, default=0)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    category = relationship("ProductCategory")

class ProductSku(Base):
    __tablename__ = "product_skus"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    stock = Column(Integer, default=-1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CardKey(Base):
    __tablename__ = "card_keys"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    key = Column(Text, nullable=False)
    status = Column(String(20), default="available")
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    sold_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class BlindBoxPool(Base):
    __tablename__ = "blind_box_pools"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    prize_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    probability = Column(Float, nullable=False)
    prize = relationship("Product", foreign_keys=[prize_id])

class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)
    value = Column(Float, nullable=False)
    min_amount = Column(Float, default=0)
    total_count = Column(Integer, default=0)
    issued_count = Column(Integer, default=0)
    max_uses = Column(Integer, default=0)
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PromoCode(Base):
    __tablename__ = "promo_codes"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    type = Column(String(20), nullable=True)
    value = Column(Float, default=0)
    min_amount = Column(Float, default=0)
    coupon_id = Column(Integer, nullable=True)
    give_count = Column(Integer, default=1)
    remark = Column(String(200), nullable=True)
    max_uses = Column(Integer, default=0)
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InviteRecord(Base):
    __tablename__ = "invite_records"
    id = Column(Integer, primary_key=True)
    inviter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    new_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(50), nullable=False)
    reward_issued = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CouponRule(Base):
    __tablename__ = "coupon_rules"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)
    coupon_id = Column(Integer, nullable=False)
    give_count = Column(Integer, default=1)
    product_id = Column(Integer, nullable=True)
    category_id = Column(Integer, nullable=True)
    min_order_amount = Column(Float, default=0)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserCoupon(Base):
    __tablename__ = "user_coupons"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    coupon = relationship("Coupon")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_no = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    total_price = Column(Float, nullable=False)
    discount = Column(Float, default=0)
    final_price = Column(Float, nullable=False)
    coupon_id = Column(Integer, nullable=True)
    status = Column(String(20), default="pending")
    delivery_type = Column(String(20), default="card_key")
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    product = relationship("Product")
    card_keys = relationship("CardKey")

class PaymentLog(Base):
    __tablename__ = "payment_logs"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, nullable=True)
    order_no = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(50), nullable=False)
    third_party_no = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")
    notify_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AppSetting(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, default="")

class MemberLevel(Base):
    __tablename__ = "member_levels"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    level = Column(Integer, unique=True, nullable=False)
    min_points = Column(Integer, default=0)
    discount = Column(Float, default=100)
    icon = Column(String(20), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class RechargeOrder(Base):
    __tablename__ = "recharge_orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(20), default="alipay")
    order_no = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="pending")
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    region = Column(String(100), default="")
    detail = Column(String(200), default="")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class RecommendProduct(Base):
    __tablename__ = "recommend_products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), default=0)
    category_name = Column(String(100), default="")
    product_ids = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ProductFile(Base):
    __tablename__ = "product_files"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    file_name = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LotteryRecord(Base):
    __tablename__ = "lottery_records"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    prize_name = Column(String(200), default="")
    prize_type = Column(String(50), default="")
    cost_points = Column(Integer, default=0)
    is_winner = Column(Boolean, default=False)
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LotteryPool(Base):
    __tablename__ = "lottery_pools"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    image_url = Column(String(500), default="")
    price = Column(Integer, default=10)
    free_daily = Column(Integer, default=0)
    points_enabled = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    pool_config = Column(Text, default="")
    settings = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Bill(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(20), default="expense")
    category = Column(String(50), default="")
    amount = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    message = Column(String(500), default="")
    order_no = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class WithdrawOrder(Base):
    __tablename__ = "withdraw_orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(20), default="alipay")
    account = Column(String(100), default="")
    real_name = Column(String(50), default="")
    status = Column(String(20), default="pending")
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AdminLog(Base):
    __tablename__ = "admin_logs"
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), default="")
    target_type = Column(String(50), default="")
    target_id = Column(Integer, nullable=True)
    message = Column(String(500), default="")
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Dict(Base):
    __tablename__ = "dicts"
    id = Column(Integer, primary_key=True)
    type = Column(String(50), default="")
    key = Column(String(50), default="")
    value = Column(Text, default="")
    name = Column(String(100), default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# ========== 新抽奖系统模型 ==========

class LotteryWheel(Base):
    """抽奖转盘"""
    __tablename__ = "lottery_wheels"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    image_url = Column(String(500), default="")
    price_type = Column(String(20), default="points")
    price_value = Column(Integer, default=10)
    free_daily = Column(Integer, default=0)
    min_points = Column(Integer, default=0)
    max_daily = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LotteryPrize(Base):
    """抽奖奖品"""
    __tablename__ = "lottery_prizes"
    id = Column(Integer, primary_key=True)
    wheel_id = Column(Integer, ForeignKey("lottery_wheels.id"), nullable=False)
    name = Column(String(100), nullable=False)
    prize_type = Column(String(50), nullable=False)
    prize_value = Column(Text, default="")
    probability = Column(Float, default=0)
    is_default = Column(Boolean, default=False)
    stock = Column(Integer, default=-1)
    total_stock = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    image_url = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LotteryTicket(Base):
    """抽奖券"""
    __tablename__ = "lottery_tickets"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    wheel_id = Column(Integer, ForeignKey("lottery_wheels.id"), nullable=True)
    status = Column(String(20), default="active")
    expires_at = Column(DateTime, nullable=True)
    source = Column(String(50), default="")
    order_id = Column(Integer, nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

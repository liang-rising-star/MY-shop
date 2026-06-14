import datetime
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import engine
from app.models import Order, User
from app.auth import require_admin

router = APIRouter()

def time_range(t):
    now = datetime.datetime.utcnow()
    if t == 0:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=1)
    elif t == 1:
        start = (now - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=1)
    elif t == 2:
        start = now - datetime.timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now + datetime.timedelta(days=1)
    elif t == 3:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now + datetime.timedelta(days=1)
    else:
        return None, None
    return start, end

@router.get("/api/admin/dashboard")
async def dashboard_data(request: Request, period: int = 0):
    await require_admin(request)
    with Session(engine) as s:
        start, end = time_range(period)
        if start:
            order_q = s.query(Order).filter(Order.created_at >= start, Order.created_at < end)
            user_q = s.query(User).filter(User.created_at >= start, User.created_at < end)
        else:
            order_q = s.query(Order)
            user_q = s.query(User)

        paid = order_q.filter(Order.status.in_(["paid", "completed"]))
        turnover = paid.with_entities(func.sum(Order.final_price)).scalar() or 0
        order_num = paid.count()
        user_register_num = user_q.count()

        all_paid = s.query(Order).filter(Order.status.in_(["paid", "completed"]))
        all_turnover = all_paid.with_entities(func.sum(Order.final_price)).scalar() or 0
        all_order_num = all_paid.count()
        total_users = s.query(User).count()

        return {
            "period": period,
            "turnover": round(turnover, 2),
            "order_num": order_num,
            "profit": round(turnover * 0.9, 2),
            "user_register_num": user_register_num,
            "all_turnover": round(all_turnover, 2),
            "all_order_num": all_order_num,
            "total_users": total_users,
            "online_amount": round(turnover * 0.7, 2),
            "recharge_amount": round(turnover * 0.3, 2),
        }

@router.get("/api/admin/dashboard/charts")
async def dashboard_charts(request: Request):
    await require_admin(request)
    now = datetime.datetime.utcnow()
    with Session(engine) as s:
        # Daily income for current month (max 31 days)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        daily_rows = s.query(
            func.strftime('%d', Order.created_at).label('day'),
            func.sum(Order.final_price).label('income')
        ).filter(
            Order.created_at >= month_start,
            Order.status.in_(["paid", "completed"])
        ).group_by('day').order_by('day').all()
        
        daily = []
        for r in daily_rows:
            daily.append({"day": int(r.day), "income": round(r.income, 2)})

        # Monthly income for last 12 months
        twelve_months_ago = now.replace(day=1) - datetime.timedelta(days=365)
        monthly_rows = s.query(
            func.strftime('%Y-%m', Order.created_at).label('month'),
            func.sum(Order.final_price).label('income')
        ).filter(
            Order.created_at >= twelve_months_ago,
            Order.status.in_(["paid", "completed"])
        ).group_by('month').order_by('month').all()

        monthly = []
        for r in monthly_rows:
            monthly.append({"month": r.month, "income": round(r.income, 2)})

        return {"daily": daily, "monthly": monthly}

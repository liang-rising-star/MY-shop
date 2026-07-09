import datetime
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import engine
from app.models import User, Bill, WithdrawOrder, RechargeOrder
from app.auth import get_current_user, require_admin

router = APIRouter()

def add_bill(user_id, bill_type, category, amount, message, order_no=None):
    with Session(engine) as s:
        u = s.query(User).filter(User.id == user_id).first()
        if not u:
            return
        
        if bill_type == "income":
            u.balance = (u.balance or 0) + amount
        elif bill_type == "expense":
            u.balance = max(0, (u.balance or 0) - amount)
        
        bill = Bill(
            user_id=user_id,
            type=bill_type,
            category=category,
            amount=amount,
            balance=u.balance,
            message=message,
            order_no=order_no
        )
        s.add(bill)
        s.commit()

@router.get("/api/user/bills")
async def get_user_bills(request: Request):
    user = await get_current_user(request)
    uid = request.state.user_id
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    bill_type = request.query_params.get("type", "")
    
    with Session(engine) as s:
        query = s.query(Bill).filter(Bill.user_id == uid)
        
        if bill_type:
            query = query.filter(Bill.type == bill_type)
        
        total = query.count()
        bills = query.order_by(Bill.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        
        return {
            "bills": [
                {
                    "id": b.id,
                    "type": b.type,
                    "category": b.category,
                    "amount": b.amount,
                    "balance": b.balance,
                    "message": b.message,
                    "order_no": b.order_no,
                    "created_at": b.created_at.isoformat()
                }
                for b in bills
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }

@router.get("/api/user/bills/summary")
async def get_bills_summary(request: Request):
    user = await get_current_user(request)
    uid = request.state.user_id
    
    with Session(engine) as s:
        income = s.query(Bill).filter(Bill.user_id == uid, Bill.type == "income").all()
        expense = s.query(Bill).filter(Bill.user_id == uid, Bill.type == "expense").all()
        
        return {
            "total_income": sum(b.amount for b in income),
            "total_expense": sum(b.amount for b in expense),
            "income_count": len(income),
            "expense_count": len(expense)
        }

@router.get("/api/admin/withdraws")
async def admin_get_withdraws(request: Request):
    await require_admin(request)
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    status = request.query_params.get("status", "")
    
    with Session(engine) as s:
        query = s.query(WithdrawOrder)
        
        if status:
            query = query.filter(WithdrawOrder.status == status)
        
        total = query.count()
        orders = query.order_by(WithdrawOrder.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        
        withdraws = []
        for w in orders:
            u = s.query(User).filter(User.id == w.user_id).first()
            withdraws.append({
                "id": w.id,
                "user_id": w.user_id,
                "username": u.username if u else "",
                "amount": w.amount,
                "method": w.method,
                "account": w.account,
                "real_name": w.real_name,
                "status": w.status,
                "processed_at": w.processed_at.isoformat() if w.processed_at else None,
                "created_at": w.created_at.isoformat()
            })
        
        return {
            "withdraws": withdraws,
            "total": total,
            "page": page,
            "page_size": page_size
        }

@router.post("/api/admin/withdraws/{wid}/process")
async def admin_process_withdraw(wid: int, data: dict, request: Request):
    await require_admin(request)
    status = data.get("status", "approved")
    
    with Session(engine) as s:
        withdraw = s.query(WithdrawOrder).filter(WithdrawOrder.id == wid).first()
        if not withdraw:
            raise HTTPException(404, "提现订单不存在")
        
        if withdraw.status != "pending":
            raise HTTPException(400, "订单已处理")
        
        withdraw.status = status
        withdraw.processed_at = datetime.datetime.utcnow()
        
        if status == "rejected":
            u = s.query(User).filter(User.id == withdraw.user_id).first()
            u.commission = (u.commission or 0) + withdraw.amount
        
        s.commit()
        
        return {"message": f"提现申请已{('通过' if status == 'approved' else '拒绝')}"}

@router.get("/api/admin/withdraws/statistics")
async def admin_withdraws_statistics(request: Request):
    await require_admin(request)
    
    with Session(engine) as s:
        today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - datetime.timedelta(days=7)
        
        pending = s.query(WithdrawOrder).filter(WithdrawOrder.status == "pending").count()
        
        today_withdraws = s.query(WithdrawOrder).filter(
            WithdrawOrder.created_at >= today,
            WithdrawOrder.status == "approved"
        ).all()
        
        week_withdraws = s.query(WithdrawOrder).filter(
            WithdrawOrder.created_at >= week_ago,
            WithdrawOrder.status == "approved"
        ).all()
        
        return {
            "pending_count": pending,
            "today": {
                "amount": sum(w.amount for w in today_withdraws),
                "count": len(today_withdraws)
            },
            "week": {
                "amount": sum(w.amount for w in week_withdraws),
                "count": len(week_withdraws)
            }
        }

@router.get("/api/admin/bills")
async def admin_get_bills(request: Request):
    await require_admin(request)
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    bill_type = request.query_params.get("type", "")
    
    with Session(engine) as s:
        query = s.query(Bill)
        
        if bill_type:
            query = query.filter(Bill.type == bill_type)
        
        total = query.count()
        bills = query.order_by(Bill.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        
        result = []
        for b in bills:
            u = s.query(User).filter(User.id == b.user_id).first()
            result.append({
                "id": b.id,
                "user_id": b.user_id,
                "username": u.username if u else "",
                "type": b.type,
                "category": b.category,
                "amount": b.amount,
                "balance": b.balance,
                "message": b.message,
                "order_no": b.order_no,
                "created_at": b.created_at.isoformat()
            })
        
        return {
            "bills": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }

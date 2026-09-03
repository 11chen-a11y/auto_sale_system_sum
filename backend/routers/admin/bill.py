from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import Bill, Customer
from schemas.schemas import BillCreate, BillUpdate, BillOut, BillList
from utils.csv_export import csv_response

router = APIRouter(prefix="/bill", tags=["账单管理"])


@router.get("/months")
async def get_available_months(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bill.bill_month).distinct().order_by(Bill.bill_month.desc()))
    return [row[0] for row in result.fetchall()]


@router.get("/customers")
async def get_billed_customers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Customer.customer_id, Customer.customer_name)
        .join(Bill, Bill.customer_id == Customer.customer_id)
        .distinct().order_by(Customer.customer_name)
    )
    return [{"customer_id": r[0], "customer_name": r[1]} for r in result.fetchall()]


@router.get("/list", response_model=BillList)
async def list_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    bill_month: str = None,
    customer_id: int = None,
    payment_status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Bill)
    count_query = select(func.count(Bill.bill_id))

    if bill_month:
        query = query.where(Bill.bill_month == bill_month)
        count_query = count_query.where(Bill.bill_month == bill_month)
    if customer_id:
        query = query.where(Bill.customer_id == customer_id)
        count_query = count_query.where(Bill.customer_id == customer_id)
    if payment_status:
        query = query.where(Bill.payment_status == payment_status)
        count_query = count_query.where(Bill.payment_status == payment_status)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Bill.bill_month.desc(), Bill.customer_id)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/create", response_model=BillOut)
async def create_bill(data: BillCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(Bill).where(
            Bill.customer_id == data.customer_id,
            Bill.bill_month == data.bill_month,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该客户该月账单已存在")

    record = Bill(
        customer_id=data.customer_id,
        bill_month=data.bill_month,
        total_kwh=data.total_kwh,
        total_amount=data.total_amount,
        payment_status=data.payment_status,
        due_date=date.fromisoformat(data.due_date) if data.due_date else None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{bill_id}", response_model=BillOut)
async def update_bill(bill_id: int, data: BillUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bill).where(Bill.bill_id == bill_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.total_kwh is not None:
        record.total_kwh = data.total_kwh
    if data.total_amount is not None:
        record.total_amount = data.total_amount
    if data.payment_status is not None:
        record.payment_status = data.payment_status
    if data.due_date is not None:
        record.due_date = date.fromisoformat(data.due_date)

    await db.commit()
    await db.refresh(record)
    return record


@router.put("/pay/{bill_id}", response_model=BillOut)
async def pay_bill(bill_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bill).where(Bill.bill_id == bill_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    record.payment_status = "已付"
    record.paid_at = datetime.now()
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{bill_id}")
async def delete_bill(bill_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bill).where(Bill.bill_id == bill_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_bills(
    bill_month: str = None,
    customer_id: int = None,
    payment_status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Bill)
    if bill_month:
        query = query.where(Bill.bill_month == bill_month)
    if customer_id:
        query = query.where(Bill.customer_id == customer_id)
    if payment_status:
        query = query.where(Bill.payment_status == payment_status)
    query = query.order_by(Bill.bill_month.desc(), Bill.customer_id)
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("账单ID", "bill_id"),
            ("客户ID", "customer_id"),
            ("账期", "bill_month"),
            ("用电量(kWh)", "total_kwh"),
            ("金额(元)", "total_amount"),
            ("付款状态", "payment_status"),
            ("到期日", "due_date"),
            ("付款时间", "paid_at"),
            ("创建时间", "created_at"),
            ("更新时间", "updated_at"),
        ],
        "bill_export.csv",
    )


@router.post("/batch")
async def batch_create(data: list[BillCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")

    # 逐条校验，避免重复数据导致整批失败
    existing = set()
    result = await db.execute(select(Bill.customer_id, Bill.bill_month))
    for row in result.fetchall():
        existing.add((row[0], row[1]))

    records = []
    skipped = 0
    for i, item in enumerate(data):
        key = (item.customer_id, item.bill_month)
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        payload = item.model_dump()
        payload["due_date"] = date.fromisoformat(payload["due_date"]) if payload.get("due_date") else None
        records.append(Bill(**payload))

    if not records:
        raise HTTPException(status_code=400, detail="全部记录已存在，未导入任何数据")

    db.add_all(records)
    await db.commit()
    msg = f"成功导入 {len(records)} 条"
    if skipped:
        msg += f"，跳过重复 {skipped} 条"
    return {"msg": msg}

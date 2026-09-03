from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import Customer
from schemas.schemas import CustomerCreate, CustomerUpdate, CustomerOut, CustomerList
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/customer", tags=["客户档案"])


@router.get("/types")
async def get_customer_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer.customer_type).distinct().where(Customer.customer_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/voltages")
async def get_voltage_levels(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer.voltage_level).distinct().where(Customer.voltage_level.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/list", response_model=CustomerList)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_name: str = None,
    customer_type: str = None,
    voltage_level: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Customer)
    count_query = select(func.count(Customer.customer_id))

    if customer_name:
        pattern = f"%{customer_name}%"
        query = query.where(Customer.customer_name.like(pattern))
        count_query = count_query.where(Customer.customer_name.like(pattern))
    if customer_type:
        query = query.where(Customer.customer_type == customer_type)
        count_query = count_query.where(Customer.customer_type == customer_type)
    if voltage_level:
        query = query.where(Customer.voltage_level == voltage_level)
        count_query = count_query.where(Customer.voltage_level == voltage_level)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Customer.customer_id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/all")
async def get_all_customers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer.customer_id, Customer.customer_name).order_by(Customer.customer_name))
    return [{"customer_id": r[0], "customer_name": r[1]} for r in result.fetchall()]


@router.post("/create", response_model=CustomerOut)
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Customer).where(Customer.customer_name == data.customer_name))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="客户名称已存在")

    record = Customer(**data.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{customer_id}", response_model=CustomerOut)
async def update_customer(customer_id: int, data: CustomerUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(record, k, v)

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{customer_id}")
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_customers(
    customer_name: str = None,
    customer_type: str = None,
    voltage_level: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Customer)
    if customer_name:
        query = query.where(Customer.customer_name.like(f"%{customer_name}%"))
    if customer_type:
        query = query.where(Customer.customer_type == customer_type)
    if voltage_level:
        query = query.where(Customer.voltage_level == voltage_level)
    query = query.order_by(Customer.customer_id.desc())
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("客户ID", "customer_id"),
            ("客户名称", "customer_name"),
            ("客户类型", "customer_type"),
            ("电压等级", "voltage_level"),
            ("合同容量(kVA)", "contract_cap"),
            ("地址", "address"),
            ("联系人", "contact_name"),
            ("联系电话", "contact_phone"),
            ("归属用户ID", "user_id"),
            ("状态", "status"),
            ("创建时间", "created_at"),
            ("更新时间", "updated_at"),
        ],
        "customer_export.csv",
    )


@router.post("/batch")
async def batch_create(data: list[CustomerCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")
    try:
        records = [Customer(**item.model_dump()) for item in data]
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入客户失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效或重复数据，请检查后重试")
    return {"msg": f"成功导入 {len(records)} 条"}

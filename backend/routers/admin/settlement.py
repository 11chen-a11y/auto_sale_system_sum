from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import Settlement
from schemas.schemas import SettlementCreate, SettlementUpdate, SettlementOut, SettlementList
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/settlement", tags=["交易结算"])


@router.get("/types")
async def get_settle_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settlement.settle_type).distinct().where(Settlement.settle_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/months")
async def get_available_months(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settlement.settle_month).distinct().order_by(Settlement.settle_month.desc()))
    return [row[0] for row in result.fetchall()]


@router.get("/list", response_model=SettlementList)
async def list_settlements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    settle_month: str = None,
    settle_type: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Settlement)
    count_query = select(func.count(Settlement.settlement_id))

    if settle_month:
        query = query.where(Settlement.settle_month == settle_month)
        count_query = count_query.where(Settlement.settle_month == settle_month)
    if settle_type:
        query = query.where(Settlement.settle_type == settle_type)
        count_query = count_query.where(Settlement.settle_type == settle_type)
    if status:
        query = query.where(Settlement.status == status)
        count_query = count_query.where(Settlement.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Settlement.settle_month.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/create", response_model=SettlementOut)
async def create_settlement(data: SettlementCreate, db: AsyncSession = Depends(get_db)):
    record = Settlement(**data.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{settlement_id}", response_model=SettlementOut)
async def update_settlement(settlement_id: int, data: SettlementUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settlement).where(Settlement.settlement_id == settlement_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(record, k, v)

    await db.commit()
    await db.refresh(record)
    return record


@router.put("/confirm/{settlement_id}", response_model=SettlementOut)
async def confirm_settlement(settlement_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settlement).where(Settlement.settlement_id == settlement_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    record.status = "已确认"
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{settlement_id}")
async def delete_settlement(settlement_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settlement).where(Settlement.settlement_id == settlement_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_settlements(
    settle_month: str = None,
    settle_type: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Settlement)
    if settle_month:
        query = query.where(Settlement.settle_month == settle_month)
    if settle_type:
        query = query.where(Settlement.settle_type == settle_type)
    if status:
        query = query.where(Settlement.status == status)
    query = query.order_by(Settlement.settle_month.desc())
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("结算ID", "settlement_id"),
            ("合约ID", "contract_id"),
            ("结算月", "settle_month"),
            ("结算类型", "settle_type"),
            ("电量(MWh)", "volume"),
            ("电价(元/MWh)", "price"),
            ("金额(元)", "amount"),
            ("状态", "status"),
            ("创建时间", "created_at"),
            ("更新时间", "updated_at"),
        ],
        "settlement_export.csv",
    )


@router.post("/batch")
async def batch_create(data: list[SettlementCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")

    try:
        records = [Settlement(**item.model_dump()) for item in data]
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入结算失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效数据，请检查后重试")

    return {"msg": f"成功导入 {len(records)} 条"}

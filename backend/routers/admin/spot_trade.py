from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import SpotTrade
from schemas.schemas import SpotTradeCreate, SpotTradeUpdate, SpotTradeOut, SpotTradeList
from utils.csv_export import csv_response

router = APIRouter(prefix="/spot-trade", tags=["现货交易"])


@router.get("/types")
async def get_trade_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SpotTrade.trade_type).distinct().where(SpotTrade.trade_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/months")
async def get_available_months(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SpotTrade.trade_month).distinct().order_by(SpotTrade.trade_month.desc()))
    return [row[0] for row in result.fetchall()]


@router.get("/list", response_model=SpotTradeList)
async def list_spot_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    trade_month: str = None,
    trade_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(SpotTrade)
    count_query = select(func.count(SpotTrade.trade_id))

    if trade_month:
        query = query.where(SpotTrade.trade_month == trade_month)
        count_query = count_query.where(SpotTrade.trade_month == trade_month)
    if trade_type:
        query = query.where(SpotTrade.trade_type == trade_type)
        count_query = count_query.where(SpotTrade.trade_type == trade_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(SpotTrade.trade_month.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/create", response_model=SpotTradeOut)
async def create_spot_trade(data: SpotTradeCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(SpotTrade).where(
            SpotTrade.trade_month == data.trade_month,
            SpotTrade.trade_type == data.trade_type,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该月交易类型已存在")

    record = SpotTrade(
        trade_month=data.trade_month,
        trade_type=data.trade_type,
        avg_price=data.avg_price,
        volume=data.volume,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{trade_id}", response_model=SpotTradeOut)
async def update_spot_trade(trade_id: int, data: SpotTradeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SpotTrade).where(SpotTrade.trade_id == trade_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.trade_month is not None:
        record.trade_month = data.trade_month
    if data.trade_type is not None:
        record.trade_type = data.trade_type
    if data.avg_price is not None:
        record.avg_price = data.avg_price
    if data.volume is not None:
        record.volume = data.volume

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{trade_id}")
async def delete_spot_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SpotTrade).where(SpotTrade.trade_id == trade_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_spot_trades(
    trade_month: str = None,
    trade_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(SpotTrade)
    if trade_month:
        query = query.where(SpotTrade.trade_month == trade_month)
    if trade_type:
        query = query.where(SpotTrade.trade_type == trade_type)
    query = query.order_by(SpotTrade.trade_month.desc())
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("交易ID", "trade_id"),
            ("交易月份", "trade_month"),
            ("交易类型", "trade_type"),
            ("均价(元/MWh)", "avg_price"),
            ("成交量(MWh)", "volume"),
            ("创建时间", "created_at"),
        ],
        "spot_trade_export.csv",
    )


@router.post("/batch")
async def batch_create(data: list[SpotTradeCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")

    # 逐条校验，避免重复数据导致整批失败
    existing = set()
    result = await db.execute(
        select(SpotTrade.trade_month, SpotTrade.trade_type)
    )
    for row in result.fetchall():
        existing.add((row[0], row[1]))

    records = []
    skipped = 0
    for i, item in enumerate(data):
        key = (item.trade_month, item.trade_type)
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        records.append(SpotTrade(**item.model_dump()))

    if not records:
        raise HTTPException(status_code=400, detail="全部记录已存在，未导入任何数据")

    db.add_all(records)
    await db.commit()
    msg = f"成功导入 {len(records)} 条"
    if skipped:
        msg += f"，跳过重复 {skipped} 条"
    return {"msg": msg}

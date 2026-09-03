from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import PowerBid
from schemas.schemas import PowerBidCreate, PowerBidUpdate, PowerBidOut, PowerBidList
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/power-bid", tags=["报价/竞价"])


@router.get("/types")
async def get_bid_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PowerBid.bid_type).distinct().where(PowerBid.bid_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/dates")
async def get_available_dates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PowerBid.bid_date).distinct().order_by(PowerBid.bid_date.desc()))
    return [str(row[0]) for row in result.fetchall()]


@router.get("/list", response_model=PowerBidList)
async def list_bids(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    bid_type: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(PowerBid)
    count_query = select(func.count(PowerBid.bid_id))

    if bid_type:
        query = query.where(PowerBid.bid_type == bid_type)
        count_query = count_query.where(PowerBid.bid_type == bid_type)
    if status:
        query = query.where(PowerBid.status == status)
        count_query = count_query.where(PowerBid.status == status)
    if date_from:
        query = query.where(PowerBid.bid_date >= date.fromisoformat(date_from))
        count_query = count_query.where(PowerBid.bid_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(PowerBid.bid_date <= date.fromisoformat(date_to))
        count_query = count_query.where(PowerBid.bid_date <= date.fromisoformat(date_to))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(PowerBid.bid_date.desc(), PowerBid.bid_id)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/chart")
async def get_bid_chart(
    bid_date: str,
    bid_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(PowerBid).where(PowerBid.bid_date == date.fromisoformat(bid_date))
    if bid_type:
        query = query.where(PowerBid.bid_type == bid_type)
    query = query.order_by(PowerBid.price.desc())
    result = await db.execute(query)
    items = result.scalars().all()
    return items


@router.post("/create", response_model=PowerBidOut)
async def create_bid(data: PowerBidCreate, db: AsyncSession = Depends(get_db)):
    record = PowerBid(
        generator_id=data.generator_id,
        bid_date=date.fromisoformat(data.bid_date),
        bid_type=data.bid_type,
        price=data.price,
        volume=data.volume,
        status="待出清",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{bid_id}", response_model=PowerBidOut)
async def update_bid(bid_id: int, data: PowerBidUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PowerBid).where(PowerBid.bid_id == bid_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.price is not None:
        record.price = data.price
    if data.volume is not None:
        record.volume = data.volume
    if data.status is not None:
        record.status = data.status

    await db.commit()
    await db.refresh(record)
    return record


@router.post("/clear")
async def clear_bids(
    bid_date: str,
    bid_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    d = date.fromisoformat(bid_date)
    query = select(PowerBid).where(
        PowerBid.bid_date == d,
        PowerBid.status == "待出清",
    )
    if bid_type:
        query = query.where(PowerBid.bid_type == bid_type)
    query = query.order_by(PowerBid.price.asc())
    result = await db.execute(query)
    bids = result.scalars().all()

    if not bids:
        raise HTTPException(status_code=400, detail="无待出清报价")

    cleared = []
    for b in bids:
        b.status = "已出清"
        b.cleared_price = b.price
        b.cleared_volume = b.volume
        cleared.append({"bid_id": b.bid_id, "price": float(b.price), "volume": float(b.volume)})

    await db.commit()
    return {"msg": f"出清完成，共 {len(cleared)} 条", "items": cleared}


@router.delete("/delete/{bid_id}")
async def delete_bid(bid_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PowerBid).where(PowerBid.bid_id == bid_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_bids(
    bid_type: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(PowerBid)
    if bid_type:
        query = query.where(PowerBid.bid_type == bid_type)
    if status:
        query = query.where(PowerBid.status == status)
    if date_from:
        query = query.where(PowerBid.bid_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(PowerBid.bid_date <= date.fromisoformat(date_to))
    query = query.order_by(PowerBid.bid_date.desc(), PowerBid.bid_id)
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("报价ID", "bid_id"),
            ("发电商ID", "generator_id"),
            ("报价日期", "bid_date"),
            ("交易类型", "bid_type"),
            ("报价(元/MWh)", "price"),
            ("申报容量(MWh)", "volume"),
            ("出清价(元/MWh)", "cleared_price"),
            ("出清量(MWh)", "cleared_volume"),
            ("状态", "status"),
            ("创建时间", "created_at"),
        ],
        "power_bid_export.csv",
    )


@router.post("/batch")
async def batch_create(data: list[PowerBidCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")

    try:
        records = []
        for item in data:
            payload = item.model_dump()
            payload["bid_date"] = date.fromisoformat(payload["bid_date"])
            payload["status"] = payload.get("status") or "待出清"
            records.append(PowerBid(**payload))
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入报价失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效数据（如重复主键或引用不存在的发电商）")

    return {"msg": f"成功导入 {len(records)} 条"}

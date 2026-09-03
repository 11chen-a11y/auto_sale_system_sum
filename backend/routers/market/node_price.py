from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import NodePrice
from schemas.schemas import NodePriceCreate, NodePriceUpdate, NodePriceOut, NodePriceList
from utils.auth import require_admin
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/node-price", tags=["节点电价"])


@router.get("/nodes")
async def get_nodes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NodePrice.node_name).distinct())
    return [row[0] for row in result.fetchall()]


@router.get("/types")
async def get_price_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NodePrice.price_type).distinct().where(NodePrice.price_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/dates")
async def get_available_dates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NodePrice.trade_date).distinct().order_by(NodePrice.trade_date.desc()))
    return [str(row[0]) for row in result.fetchall()]


@router.get("/list", response_model=NodePriceList)
async def list_node_prices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    node_name: str = None,
    price_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(NodePrice)
    count_query = select(func.count(NodePrice.price_id))

    if node_name:
        query = query.where(NodePrice.node_name == node_name)
        count_query = count_query.where(NodePrice.node_name == node_name)
    if price_type:
        query = query.where(NodePrice.price_type == price_type)
        count_query = count_query.where(NodePrice.price_type == price_type)
    if date_from:
        query = query.where(NodePrice.trade_date >= date.fromisoformat(date_from))
        count_query = count_query.where(NodePrice.trade_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(NodePrice.trade_date <= date.fromisoformat(date_to))
        count_query = count_query.where(NodePrice.trade_date <= date.fromisoformat(date_to))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(NodePrice.trade_date.desc(), NodePrice.node_name)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/chart", response_model=list[NodePriceOut])
async def get_chart_data(
    trade_date: str,
    node_name: str = None,
    price_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(NodePrice).where(NodePrice.trade_date == date.fromisoformat(trade_date))
    if node_name:
        query = query.where(NodePrice.node_name == node_name)
    if price_type:
        query = query.where(NodePrice.price_type == price_type)
    result = await db.execute(query)
    items = result.scalars().all()
    if not items:
        raise HTTPException(status_code=404, detail="该日期无电价数据")
    return items


@router.post("/create", response_model=NodePriceOut, dependencies=[Depends(require_admin)])
async def create_node_price(data: NodePriceCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(NodePrice).where(
            NodePrice.trade_date == date.fromisoformat(data.trade_date),
            NodePrice.node_name == data.node_name,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该日期节点已存在")

    record = NodePrice(
        trade_date=date.fromisoformat(data.trade_date),
        node_name=data.node_name,
        price_type=data.price_type,
        slots=data.slots,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{price_id}", response_model=NodePriceOut, dependencies=[Depends(require_admin)])
async def update_node_price(price_id: int, data: NodePriceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NodePrice).where(NodePrice.price_id == price_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.price_type is not None:
        record.price_type = data.price_type
    if data.slots is not None:
        record.slots = data.slots

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{price_id}", dependencies=[Depends(require_admin)])
async def delete_node_price(price_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NodePrice).where(NodePrice.price_id == price_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_node_prices(
    node_name: str = None,
    price_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(NodePrice)
    if node_name:
        query = query.where(NodePrice.node_name == node_name)
    if price_type:
        query = query.where(NodePrice.price_type == price_type)
    if date_from:
        query = query.where(NodePrice.trade_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(NodePrice.trade_date <= date.fromisoformat(date_to))
    query = query.order_by(NodePrice.trade_date.desc(), NodePrice.node_name)
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("电价ID", "price_id"),
            ("交易日期", "trade_date"),
            ("节点", "node_name"),
            ("价格类型", "price_type"),
            ("96点数据(JSON)", "slots"),
            ("创建时间", "created_at"),
        ],
        "node_price_export.csv",
    )


@router.post("/batch", dependencies=[Depends(require_admin)])
async def batch_create(data: list[NodePriceCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")
    try:
        records = [NodePrice(**item.model_dump()) for item in data]
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入节点电价失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效或重复数据，请检查后重试")
    return {"msg": f"成功导入 {len(records)} 条"}

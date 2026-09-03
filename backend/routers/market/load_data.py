from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import LoadData
from schemas.schemas import LoadDataCreate, LoadDataUpdate, LoadDataOut, LoadDataList
from utils.auth import require_admin
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/load-data", tags=["实际负荷"])


@router.get("/types")
async def get_data_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LoadData.data_type).distinct().where(LoadData.data_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/dates")
async def get_available_dates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LoadData.record_date).distinct().order_by(LoadData.record_date.desc()))
    return [str(row[0]) for row in result.fetchall()]


@router.get("/list", response_model=LoadDataList)
async def list_load_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    data_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(LoadData)
    count_query = select(func.count(LoadData.load_id))

    if data_type:
        query = query.where(LoadData.data_type == data_type)
        count_query = count_query.where(LoadData.data_type == data_type)
    if date_from:
        query = query.where(LoadData.record_date >= date.fromisoformat(date_from))
        count_query = count_query.where(LoadData.record_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(LoadData.record_date <= date.fromisoformat(date_to))
        count_query = count_query.where(LoadData.record_date <= date.fromisoformat(date_to))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(LoadData.record_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/chart", response_model=list[LoadDataOut])
async def get_chart_data(
    record_date: str,
    data_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(LoadData).where(LoadData.record_date == date.fromisoformat(record_date))
    if data_type:
        query = query.where(LoadData.data_type == data_type)
    result = await db.execute(query)
    items = result.scalars().all()
    if not items:
        raise HTTPException(status_code=404, detail="该日期无负荷数据")
    return items


@router.post("/create", response_model=LoadDataOut, dependencies=[Depends(require_admin)])
async def create_load_data(data: LoadDataCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(LoadData).where(
            LoadData.record_date == date.fromisoformat(data.record_date),
            LoadData.data_type == data.data_type,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该日期类型已存在")

    record = LoadData(
        record_date=date.fromisoformat(data.record_date),
        data_type=data.data_type,
        slots=data.slots,
        total_kwh=data.total_kwh,
        remarks=data.remarks,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{load_id}", response_model=LoadDataOut, dependencies=[Depends(require_admin)])
async def update_load_data(load_id: int, data: LoadDataUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LoadData).where(LoadData.load_id == load_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.data_type is not None:
        record.data_type = data.data_type
    if data.slots is not None:
        record.slots = data.slots
    if data.total_kwh is not None:
        record.total_kwh = data.total_kwh
    if data.remarks is not None:
        record.remarks = data.remarks

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{load_id}", dependencies=[Depends(require_admin)])
async def delete_load_data(load_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LoadData).where(LoadData.load_id == load_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_load_data(
    data_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(LoadData)
    if data_type:
        query = query.where(LoadData.data_type == data_type)
    if date_from:
        query = query.where(LoadData.record_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(LoadData.record_date <= date.fromisoformat(date_to))
    query = query.order_by(LoadData.record_date.desc())
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("负荷ID", "load_id"),
            ("客户ID", "customer_id"),
            ("日期", "record_date"),
            ("数据类型", "data_type"),
            ("96点数据(JSON)", "slots"),
            ("日总电量(kWh)", "total_kwh"),
            ("备注", "remarks"),
            ("创建时间", "created_at"),
        ],
        "load_data_export.csv",
    )


@router.post("/batch", dependencies=[Depends(require_admin)])
async def batch_create(data: list[LoadDataCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")
    try:
        records = [LoadData(**item.model_dump()) for item in data]
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入负荷数据失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效或重复数据，请检查后重试")
    return {"msg": f"成功导入 {len(records)} 条"}

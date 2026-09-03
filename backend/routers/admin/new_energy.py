from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import NewEnergy
from schemas.schemas import NewEnergyCreate, NewEnergyUpdate, NewEnergyOut, NewEnergyList
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/new-energy", tags=["新能源出力"])


@router.get("/stations")
async def get_stations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewEnergy.station_name).distinct())
    return [row[0] for row in result.fetchall()]


@router.get("/types")
async def get_energy_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewEnergy.energy_type).distinct().where(NewEnergy.energy_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/dates")
async def get_available_dates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewEnergy.record_date).distinct().order_by(NewEnergy.record_date.desc()))
    return [str(row[0]) for row in result.fetchall()]


@router.get("/list", response_model=NewEnergyList)
async def list_new_energy(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    station_name: str = None,
    energy_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(NewEnergy)
    count_query = select(func.count(NewEnergy.energy_id))

    if station_name:
        query = query.where(NewEnergy.station_name == station_name)
        count_query = count_query.where(NewEnergy.station_name == station_name)
    if energy_type:
        query = query.where(NewEnergy.energy_type == energy_type)
        count_query = count_query.where(NewEnergy.energy_type == energy_type)
    if date_from:
        query = query.where(NewEnergy.record_date >= date.fromisoformat(date_from))
        count_query = count_query.where(NewEnergy.record_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(NewEnergy.record_date <= date.fromisoformat(date_to))
        count_query = count_query.where(NewEnergy.record_date <= date.fromisoformat(date_to))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(NewEnergy.record_date.desc(), NewEnergy.station_name)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/chart", response_model=list[NewEnergyOut])
async def get_chart_data(
    record_date: str,
    station_name: str = None,
    energy_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(NewEnergy).where(NewEnergy.record_date == date.fromisoformat(record_date))
    if station_name:
        query = query.where(NewEnergy.station_name == station_name)
    if energy_type:
        query = query.where(NewEnergy.energy_type == energy_type)
    result = await db.execute(query)
    items = result.scalars().all()
    if not items:
        raise HTTPException(status_code=404, detail="该日期无新能源数据")
    return items


@router.post("/create", response_model=NewEnergyOut)
async def create_new_energy(data: NewEnergyCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(NewEnergy).where(
            NewEnergy.record_date == date.fromisoformat(data.record_date),
            NewEnergy.station_name == data.station_name,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该日期场站已存在")

    record = NewEnergy(
        record_date=date.fromisoformat(data.record_date),
        station_name=data.station_name,
        energy_type=data.energy_type,
        forecast_slots=data.forecast_slots,
        actual_slots=data.actual_slots,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{energy_id}", response_model=NewEnergyOut)
async def update_new_energy(energy_id: int, data: NewEnergyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewEnergy).where(NewEnergy.energy_id == energy_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.station_name is not None:
        record.station_name = data.station_name
    if data.energy_type is not None:
        record.energy_type = data.energy_type
    if data.forecast_slots is not None:
        record.forecast_slots = data.forecast_slots
    if data.actual_slots is not None:
        record.actual_slots = data.actual_slots

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{energy_id}")
async def delete_new_energy(energy_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewEnergy).where(NewEnergy.energy_id == energy_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_new_energy(
    station_name: str = None,
    energy_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(NewEnergy)
    if station_name:
        query = query.where(NewEnergy.station_name == station_name)
    if energy_type:
        query = query.where(NewEnergy.energy_type == energy_type)
    if date_from:
        query = query.where(NewEnergy.record_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(NewEnergy.record_date <= date.fromisoformat(date_to))
    query = query.order_by(NewEnergy.record_date.desc(), NewEnergy.station_name)
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("记录ID", "energy_id"),
            ("日期", "record_date"),
            ("场站", "station_name"),
            ("能源类型", "energy_type"),
            ("预测出力(JSON)", "forecast_slots"),
            ("实际出力(JSON)", "actual_slots"),
            ("创建时间", "created_at"),
        ],
        "new_energy_export.csv",
    )


@router.post("/batch")
async def batch_create(data: list[NewEnergyCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")
    try:
        records = [NewEnergy(**item.model_dump()) for item in data]
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入新能源数据失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效或重复数据，请检查后重试")
    return {"msg": f"成功导入 {len(records)} 条"}

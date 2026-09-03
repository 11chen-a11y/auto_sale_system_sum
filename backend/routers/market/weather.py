from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import WeatherData
from schemas.schemas import WeatherCreate, WeatherUpdate, WeatherOut, WeatherList
from utils.auth import require_admin
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/weather", tags=["天气数据"])


@router.get("/stations")
async def get_stations(city: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(WeatherData.station_name).distinct().where(WeatherData.station_name.isnot(None))
    if city:
        stmt = stmt.where(WeatherData.city == city)
    result = await db.execute(stmt)
    return [row[0] for row in result.fetchall()]


@router.get("/cities")
async def get_cities(station_name: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(WeatherData.city).distinct().where(WeatherData.city.isnot(None))
    if station_name:
        stmt = stmt.where(WeatherData.station_name == station_name)
    result = await db.execute(stmt)
    return [row[0] for row in result.fetchall()]


@router.get("/types")
async def get_data_types(station_name: str = None, city: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(WeatherData.data_type).distinct().where(WeatherData.data_type.isnot(None))
    if station_name:
        stmt = stmt.where(WeatherData.station_name == station_name)
    if city:
        stmt = stmt.where(WeatherData.city == city)
    result = await db.execute(stmt)
    return [row[0] for row in result.fetchall()]


@router.get("/dates")
async def get_available_dates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeatherData.record_date).distinct().order_by(WeatherData.record_date.desc()))
    return [str(row[0]) for row in result.fetchall()]


@router.get("/list", response_model=WeatherList)
async def list_weather(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    station_name: str = None,
    city: str = None,
    data_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WeatherData)
    count_query = select(func.count(WeatherData.weather_id))

    if station_name:
        query = query.where(WeatherData.station_name == station_name)
        count_query = count_query.where(WeatherData.station_name == station_name)
    if city:
        query = query.where(WeatherData.city == city)
        count_query = count_query.where(WeatherData.city == city)
    if data_type:
        query = query.where(WeatherData.data_type == data_type)
        count_query = count_query.where(WeatherData.data_type == data_type)
    if date_from:
        query = query.where(WeatherData.record_date >= date.fromisoformat(date_from))
        count_query = count_query.where(WeatherData.record_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(WeatherData.record_date <= date.fromisoformat(date_to))
        count_query = count_query.where(WeatherData.record_date <= date.fromisoformat(date_to))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(WeatherData.record_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/chart")
async def get_chart_data(
    date_from: str = Query(...),
    date_to: str = Query(...),
    station_name: str = None,
    city: str = None,
    db: AsyncSession = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)
    query = select(WeatherData).where(WeatherData.record_date.between(d_from, d_to))
    if station_name:
        query = query.where(WeatherData.station_name == station_name)
    if city:
        query = query.where(WeatherData.city == city)
    query = query.order_by(WeatherData.record_date)
    result = await db.execute(query)
    items = result.scalars().all()
    return items


@router.post("/create", response_model=WeatherOut, dependencies=[Depends(require_admin)])
async def create_weather(data: WeatherCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(WeatherData).where(
            WeatherData.station_name == data.station_name,
            WeatherData.record_date == date.fromisoformat(data.record_date),
            WeatherData.data_type == data.data_type,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该站该日数据类型已存在")

    record = WeatherData(
        station_name=data.station_name,
        city=data.city,
        record_date=date.fromisoformat(data.record_date),
        data_type=data.data_type,
        temperature=data.temperature,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{weather_id}", response_model=WeatherOut, dependencies=[Depends(require_admin)])
async def update_weather(weather_id: int, data: WeatherUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeatherData).where(WeatherData.weather_id == weather_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.station_name is not None:
        record.station_name = data.station_name
    if data.city is not None:
        record.city = data.city
    if data.data_type is not None:
        record.data_type = data.data_type
    if data.temperature is not None:
        record.temperature = data.temperature

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{weather_id}", dependencies=[Depends(require_admin)])
async def delete_weather(weather_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeatherData).where(WeatherData.weather_id == weather_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_weather(
    station_name: str = None,
    city: str = None,
    data_type: str = None,
    date_from: str = None,
    date_to: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WeatherData)
    if station_name:
        query = query.where(WeatherData.station_name == station_name)
    if city:
        query = query.where(WeatherData.city == city)
    if data_type:
        query = query.where(WeatherData.data_type == data_type)
    if date_from:
        query = query.where(WeatherData.record_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(WeatherData.record_date <= date.fromisoformat(date_to))
    query = query.order_by(WeatherData.record_date.desc())
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("天气ID", "weather_id"),
            ("站点", "station_name"),
            ("城市", "city"),
            ("日期", "record_date"),
            ("数据类型", "data_type"),
            ("温度(°C)", "temperature"),
            ("创建时间", "created_at"),
        ],
        "weather_export.csv",
    )


@router.post("/batch", dependencies=[Depends(require_admin)])
async def batch_create(data: list[WeatherCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")
    try:
        records = [WeatherData(**item.model_dump()) for item in data]
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入天气数据失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效或重复数据，请检查后重试")
    return {"msg": f"成功导入 {len(records)} 条"}

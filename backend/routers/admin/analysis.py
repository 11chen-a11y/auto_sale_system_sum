from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import LoadData, NodePrice, NewEnergy, WeatherData, Customer, Bill

router = APIRouter(prefix="/analysis", tags=["关联分析"])


# ─── 负荷 vs 电价 ──────────────────────────────────────
@router.get("/load-vs-price")
async def load_vs_price(record_date: str, db: AsyncSession = Depends(get_db)):
    load = await db.execute(
        select(LoadData).where(LoadData.record_date == date.fromisoformat(record_date))
    )
    price = await db.execute(
        select(NodePrice).where(NodePrice.trade_date == date.fromisoformat(record_date))
    )
    load_items = load.scalars().all()
    price_items = price.scalars().all()
    return {
        "date": record_date,
        "load": [{"id": r.load_id, "data_type": r.data_type, "slots": r.slots} for r in load_items],
        "price": [{"id": r.price_id, "node_name": r.node_name, "price_type": r.price_type, "slots": r.slots} for r in price_items],
    }


# ─── 负荷 vs 新能源出力（含净负荷） ──────────────────────
@router.get("/load-vs-new-energy")
async def load_vs_new_energy(record_date: str, db: AsyncSession = Depends(get_db)):
    load = await db.execute(
        select(LoadData).where(LoadData.record_date == date.fromisoformat(record_date))
    )
    new_energy = await db.execute(
        select(NewEnergy).where(NewEnergy.record_date == date.fromisoformat(record_date))
    )
    load_items = load.scalars().all()
    ne_items = new_energy.scalars().all()

    net_slots = None
    if load_items and ne_items:
        load_slots = {}
        for r in load_items:
            if r.slots:
                for k, v in r.slots.items():
                    load_slots[k] = load_slots.get(k, 0) + float(v)
        ne_slots = {}
        for r in ne_items:
            if r.actual_slots:
                for k, v in r.actual_slots.items():
                    ne_slots[k] = ne_slots.get(k, 0) + float(v)
        all_keys = sorted(set(list(load_slots.keys()) + list(ne_slots.keys())))
        net_slots = {}
        for k in all_keys:
            net_slots[k] = load_slots.get(k, 0) - ne_slots.get(k, 0)

    return {
        "date": record_date,
        "load": [{"id": r.load_id, "data_type": r.data_type, "slots": r.slots} for r in load_items],
        "new_energy": [{"id": r.energy_id, "station_name": r.station_name, "energy_type": r.energy_type, "actual_slots": r.actual_slots} for r in ne_items],
        "net_load": net_slots,
    }


# ─── 负荷 vs 天气 ──────────────────────────────────────
@router.get("/load-vs-weather")
async def load_vs_weather(
    date_from: str = Query(...),
    date_to: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    load_rows = await db.execute(
        select(LoadData.record_date, LoadData.slots)
        .where(LoadData.record_date.between(d_from, d_to))
    )
    weather_rows = await db.execute(
        select(WeatherData.record_date, WeatherData.temperature)
        .where(WeatherData.record_date.between(d_from, d_to))
    )

    daily_load = {}
    for r in load_rows.fetchall():
        if r.slots:
            vals = [float(v) for v in r.slots.values() if v is not None]
            if vals:
                daily_load[str(r[0])] = {
                    "avg": sum(vals) / len(vals),
                    "max": max(vals),
                    "min": min(vals),
                    "sum": sum(vals),
                }

    daily_weather = {}
    for r in weather_rows.fetchall():
        k = str(r[0])
        if r.temperature is not None:
            if k not in daily_weather:
                daily_weather[k] = []
            daily_weather[k].append(float(r.temperature))

    points = []
    all_dates = sorted(set(list(daily_load.keys()) + list(daily_weather.keys())))
    for d in all_dates:
        if d in daily_load and d in daily_weather:
            points.append({
                "date": d,
                "avg_load": daily_load[d]["avg"],
                "max_load": daily_load[d]["max"],
                "min_load": daily_load[d]["min"],
                "sum_load": daily_load[d]["sum"],
                "avg_temp": sum(daily_weather[d]) / len(daily_weather[d]),
                "max_temp": max(daily_weather[d]),
                "min_temp": min(daily_weather[d]),
            })

    return {"date_from": date_from, "date_to": date_to, "points": points}


# ─── 客户用电分析（按月） ──────────────────────────────
@router.get("/customer-consumption")
async def customer_consumption(
    year_month: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(
        Customer.customer_id,
        Customer.customer_name,
        Customer.customer_type,
        Customer.voltage_level,
        Bill.bill_month,
        Bill.total_kwh,
        Bill.total_amount,
        Bill.payment_status,
    ).join(Bill, Bill.customer_id == Customer.customer_id)

    if year_month:
        query = query.where(Bill.bill_month == year_month)

    query = query.order_by(Bill.bill_month.desc(), Customer.customer_name)
    result = await db.execute(query)

    rows = []
    for r in result.fetchall():
        rows.append({
            "customer_id": r.customer_id,
            "customer_name": r.customer_name,
            "customer_type": r.customer_type,
            "voltage_level": r.voltage_level,
            "bill_month": r.bill_month,
            "total_kwh": float(r.total_kwh) if r.total_kwh else 0,
            "total_amount": float(r.total_amount) if r.total_amount else 0,
            "payment_status": r.payment_status,
        })

    months = await db.execute(
        select(Bill.bill_month).distinct().order_by(Bill.bill_month.desc())
    )
    available_months = [r[0] for r in months.fetchall()]

    return {"items": rows, "available_months": available_months}


# ─── 完整链路（天气→负荷→电价→新能源）────────────────
@router.get("/full-chain")
async def full_chain(record_date: str, db: AsyncSession = Depends(get_db)):
    d = date.fromisoformat(record_date)

    load = (await db.execute(select(LoadData).where(LoadData.record_date == d))).scalars().all()
    price = (await db.execute(select(NodePrice).where(NodePrice.trade_date == d))).scalars().all()
    new_energy = (await db.execute(select(NewEnergy).where(NewEnergy.record_date == d))).scalars().all()
    weather = (await db.execute(select(WeatherData).where(WeatherData.record_date == d))).scalars().all()

    return {
        "date": record_date,
        "load": [{"data_type": r.data_type, "slots": r.slots} for r in load],
        "price": [{"node_name": r.node_name, "price_type": r.price_type, "slots": r.slots} for r in price],
        "new_energy": [{"station_name": r.station_name, "energy_type": r.energy_type, "actual_slots": r.actual_slots} for r in new_energy],
        "weather": [{"station_name": r.station_name, "city": r.city, "data_type": r.data_type, "temperature": r.temperature} for r in weather],
    }

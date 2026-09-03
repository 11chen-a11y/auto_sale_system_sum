# 负荷预测分析
# 基于历史负荷数据，使用相似日平均法 + 天气加权模型进行预测

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import math

from config.conf_db import get_db
from models.models import LoadData, WeatherData

router = APIRouter(prefix="/load-forecast", tags=["负荷预测"])


# ─── 获取历史负荷（用于展示） ──────────────────────────
@router.get("/history")
async def get_history(
    date_from: str = Query(...),
    date_to: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    rows = await db.execute(
        select(LoadData)
        .where(LoadData.record_date.between(d_from, d_to))
        .order_by(LoadData.record_date)
    )
    items = rows.scalars().all()

    daily = {}
    for r in items:
        key = str(r.record_date)
        if key not in daily:
            daily[key] = {"date": key, "slots": {}, "total_kwh": 0}
        if r.slots:
            for k, v in r.slots.items():
                daily[key]["slots"][k] = daily[key]["slots"].get(k, 0) + float(v)
        if r.total_kwh:
            daily[key]["total_kwh"] += float(r.total_kwh)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "days": sorted(daily.values(), key=lambda x: x["date"]),
    }


# ─── 负荷预测（相似日平均法） ──────────────────────────
@router.get("/predict")
async def predict_load(
    target_date: str = Query(...),
    lookback_weeks: int = Query(4, ge=1, le=8),
    db: AsyncSession = Depends(get_db),
):
    d = date.fromisoformat(target_date)
    target_weekday = d.weekday()

    ref_dates = []
    for w in range(1, lookback_weeks + 1):
        ref_dates.append(d - timedelta(weeks=w))

    rows = await db.execute(
        select(LoadData)
        .where(LoadData.record_date.in_(ref_dates))
        .order_by(LoadData.record_date)
    )
    items = rows.scalars().all()

    if not items:
        return {
            "target_date": target_date,
            "lookback_weeks": lookback_weeks,
            "predicted_slots": None,
            "message": "历史数据不足，无法预测",
        }

    slot_sum = {}
    slot_count = {}
    for r in items:
        if r.slots:
            for k, v in r.slots.items():
                slot_sum[k] = slot_sum.get(k, 0) + float(v)
                slot_count[k] = slot_count.get(k, 0) + 1

    predicted = {}
    for k in sorted(slot_sum.keys(), key=float):
        predicted[k] = round(slot_sum[k] / slot_count[k], 2)

    total_forecast = sum(predicted.values())

    return {
        "target_date": target_date,
        "lookback_weeks": lookback_weeks,
        "predicted_slots": predicted,
        "total_kwh": round(total_forecast, 2),
        "reference_dates": [str(x) for x in ref_dates],
    }


# ─── 天气加权负荷预测 ──────────────────────────────────
def _temperature_weight(ref_temp, target_temp, sigma=5.0):
    if ref_temp is None or target_temp is None:
        return 1.0
    diff = abs(ref_temp - target_temp)
    return math.exp(-(diff ** 2) / (2 * sigma ** 2))


@router.get("/predict-weather")
async def predict_load_with_weather(
    target_date: str = Query(...),
    lookback_weeks: int = Query(4, ge=1, le=8),
    sigma: float = Query(5.0, ge=1.0, le=20.0, description="温度相似度核宽度"),
    db: AsyncSession = Depends(get_db),
):
    d = date.fromisoformat(target_date)
    target_weekday = d.weekday()

    ref_dates = []
    for w in range(1, lookback_weeks + 1):
        ref_dates.append(d - timedelta(weeks=w))

    # 查询参考日负荷数据
    rows = await db.execute(
        select(LoadData)
        .where(LoadData.record_date.in_(ref_dates))
        .order_by(LoadData.record_date)
    )
    load_items = rows.scalars().all()

    if not load_items:
        return {
            "target_date": target_date,
            "lookback_weeks": lookback_weeks,
            "predicted_slots": None,
            "message": "历史负荷数据不足，无法预测",
        }

    # 查询参考日天气数据（日均温）
    weather_rows = await db.execute(
        select(WeatherData.record_date, WeatherData.temperature)
        .where(WeatherData.record_date.in_(ref_dates))
        .where(WeatherData.data_type == "日均温")
    )
    ref_weather = {}
    for r in weather_rows.fetchall():
        k = str(r[0])
        if r.temperature is not None:
            ref_weather[k] = float(r.temperature)

    # 查询目标日天气预测（如果有）
    target_weather_rows = await db.execute(
        select(WeatherData.temperature)
        .where(WeatherData.record_date == d)
        .where(WeatherData.data_type == "日均温")
    )
    target_temps = [float(r[0]) for r in target_weather_rows.fetchall() if r[0] is not None]
    target_temp = sum(target_temps) / len(target_temps) if target_temps else None

    # 构建参考日数据结构
    ref_data = []
    for r in load_items:
        d_key = str(r.record_date)
        temp = ref_weather.get(d_key)
        weight = _temperature_weight(temp, target_temp, sigma)
        if r.slots:
            ref_data.append({
                "date": d_key,
                "temperature": temp,
                "weight": weight,
                "slots": {k: float(v) for k, v in r.slots.items()},
            })

    if not ref_data:
        return {
            "target_date": target_date,
            "lookback_weeks": lookback_weeks,
            "predicted_slots": None,
            "message": "参考数据不足，无法预测",
        }

    # 温度加权平均
    total_weight = sum(r["weight"] for r in ref_data)
    all_keys = sorted(set(k for r in ref_data for k in r["slots"]), key=float)

    weighted_sum = {}
    weighted_sq_sum = {}
    for k in all_keys:
        weighted_sum[k] = 0
        weighted_sq_sum[k] = 0

    for r in ref_data:
        w = r["weight"]
        for k in all_keys:
            v = r["slots"].get(k, 0)
            weighted_sum[k] += w * v
            weighted_sq_sum[k] += w * (v ** 2)

    predicted = {}
    confidence_lower = {}
    confidence_upper = {}
    for k in all_keys:
        mean = weighted_sum[k] / total_weight if total_weight > 0 else 0
        predicted[k] = round(mean, 2)
        # 加权标准差
        variance = (weighted_sq_sum[k] / total_weight) - (mean ** 2) if total_weight > 0 else 0
        std = max(0, math.sqrt(variance))
        confidence_lower[k] = round(mean - 1.96 * std, 2)
        confidence_upper[k] = round(mean + 1.96 * std, 2)

    total_forecast = sum(predicted.values())

    # 计算参考日温度分布
    temps = [r["temperature"] for r in ref_data if r["temperature"] is not None]

    return {
        "target_date": target_date,
        "lookback_weeks": lookback_weeks,
        "sigma": sigma,
        "predicted_slots": predicted,
        "confidence_lower": confidence_lower,
        "confidence_upper": confidence_upper,
        "total_kwh": round(total_forecast, 2),
        "reference_dates": [r["date"] for r in ref_data],
        "target_temperature": target_temp,
        "reference_temperatures": {
            r["date"]: r["temperature"] for r in ref_data if r["temperature"] is not None
        },
        "temperature_summary": {
            "avg": round(sum(temps) / len(temps), 2) if temps else None,
            "min": round(min(temps), 2) if temps else None,
            "max": round(max(temps), 2) if temps else None,
            "target": target_temp,
        },
    }

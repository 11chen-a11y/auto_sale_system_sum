# 价格趋势分析
# 对节点电价进行趋势分析、移动平均、节点对比、波动率分析、季节性对比

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import math

from config.conf_db import get_db
from models.models import NodePrice, SpotTrade, LoadData, WeatherData

router = APIRouter(prefix="/price-trend", tags=["价格趋势"])


# ─── 日期范围趋势（日均价、最高、最低） ─────────────────
@router.get("/trend")
async def price_trend(
    date_from: str = Query(...),
    date_to: str = Query(...),
    node_name: str = None,
    price_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    query = select(NodePrice).where(NodePrice.trade_date.between(d_from, d_to))
    if node_name:
        query = query.where(NodePrice.node_name == node_name)
    if price_type:
        query = query.where(NodePrice.price_type == price_type)
    query = query.order_by(NodePrice.trade_date, NodePrice.node_name)

    rows = await db.execute(query)
    items = rows.scalars().all()

    daily = {}
    for r in items:
        key = str(r.trade_date)
        if key not in daily:
            daily[key] = {"date": key, "slots": {}, "count": 0}
        if r.slots:
            for k, v in r.slots.items():
                daily[key]["slots"][k] = daily[key]["slots"].get(k, 0) + float(v)
                daily[key]["count"] += 1

    result = []
    for d_key in sorted(daily.keys()):
        vals = list(daily[d_key]["slots"].values())
        if vals:
            result.append({
                "date": d_key,
                "avg_price": round(sum(vals) / len(vals), 2),
                "max_price": round(max(vals), 2),
                "min_price": round(min(vals), 2),
            })

    ma5 = []
    for i in range(len(result)):
        if i < 4:
            ma5.append(None)
        else:
            avg = round(sum(r["avg_price"] for r in result[i - 4 : i + 1]) / 5, 2)
            ma5.append(avg)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "node_name": node_name,
        "price_type": price_type,
        "daily": result,
        "ma5": ma5,
    }


# ─── 节点对比（多节点同日期范围） ──────────────────────
@router.get("/comparison")
async def price_comparison(
    date_from: str = Query(...),
    date_to: str = Query(...),
    nodes: str = Query(None, description="逗号分隔的节点名"),
    db: AsyncSession = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    query = select(NodePrice).where(NodePrice.trade_date.between(d_from, d_to))
    if nodes:
        node_list = [n.strip() for n in nodes.split(",")]
        query = query.where(NodePrice.node_name.in_(node_list))

    rows = await db.execute(query.order_by(NodePrice.trade_date, NodePrice.node_name))
    items = rows.scalars().all()

    by_node = {}
    for r in items:
        key = r.node_name
        if key not in by_node:
            by_node[key] = {}
        date_key = str(r.trade_date)
        if date_key not in by_node[key]:
            by_node[key][date_key] = []
        if r.slots:
            by_node[key][date_key].extend(float(v) for v in r.slots.values())

    node_data = {}
    for node, dates in by_node.items():
        series = []
        for d_key in sorted(dates.keys()):
            vals = dates[d_key]
            if vals:
                series.append({
                    "date": d_key,
                    "avg_price": round(sum(vals) / len(vals), 2),
                })
        node_data[node] = series

    return {"date_from": date_from, "date_to": date_to, "nodes": node_data}


# ─── 现货市场价格趋势 ──────────────────────────────────
@router.get("/spot-trend")
async def spot_price_trend(
    trade_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(SpotTrade).order_by(SpotTrade.trade_month)
    if trade_type:
        query = query.where(SpotTrade.trade_type == trade_type)

    rows = await db.execute(query)
    items = rows.scalars().all()

    result = [
        {
            "trade_month": r.trade_month,
            "trade_type": r.trade_type,
            "avg_price": float(r.avg_price) if r.avg_price else 0,
            "volume": float(r.volume) if r.volume else 0,
        }
        for r in items
    ]

    types = await db.execute(
        select(SpotTrade.trade_type).distinct().where(SpotTrade.trade_type.isnot(None))
    )
    available_types = [r[0] for r in types.fetchall()]

    return {"items": result, "available_types": available_types}


# ─── 价格波动率分析 ────────────────────────────────────
@router.get("/volatility")
async def price_volatility(
    date_from: str = Query(...),
    date_to: str = Query(...),
    node_name: str = None,
    price_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    query = select(NodePrice).where(NodePrice.trade_date.between(d_from, d_to))
    if node_name:
        query = query.where(NodePrice.node_name == node_name)
    if price_type:
        query = query.where(NodePrice.price_type == price_type)
    query = query.order_by(NodePrice.trade_date)

    rows = await db.execute(query)
    items = rows.scalars().all()

    daily = {}
    for r in items:
        key = str(r.trade_date)
        if key not in daily:
            daily[key] = {"vals": []}
        if r.slots:
            daily[key]["vals"].extend(float(v) for v in r.slots.values())

    result = []
    for d_key in sorted(daily.keys()):
        vals = daily[d_key]["vals"]
        if not vals:
            continue
        n = len(vals)
        mean = sum(vals) / n
        variance = sum((v - mean) ** 2 for v in vals) / n
        std = math.sqrt(variance)
        cv = std / mean if mean != 0 else 0
        p25 = sorted(vals)[int(n * 0.25)]
        p75 = sorted(vals)[int(n * 0.75)]
        result.append({
            "date": d_key,
            "avg_price": round(mean, 2),
            "std_dev": round(std, 2),
            "cv": round(cv, 4),
            "range": round(max(vals) - min(vals), 2),
            "p25": round(p25, 2),
            "p75": round(p75, 2),
            "max_price": round(max(vals), 2),
            "min_price": round(min(vals), 2),
        })

    # 整体统计
    all_vals = [v for d in daily.values() for v in d["vals"]]
    overall = {}
    if all_vals:
        n = len(all_vals)
        m = sum(all_vals) / n
        overall = {
            "avg_price": round(m, 2),
            "std_dev": round(math.sqrt(sum((v - m) ** 2 for v in all_vals) / n), 2),
            "cv": round(math.sqrt(sum((v - m) ** 2 for v in all_vals) / n) / m, 4) if m != 0 else 0,
            "max": round(max(all_vals), 2),
            "min": round(min(all_vals), 2),
        }

    return {
        "date_from": date_from,
        "date_to": date_to,
        "node_name": node_name,
        "price_type": price_type,
        "daily": result,
        "overall": overall,
    }


# ─── 季节性价格对比（月同比） ──────────────────────────
@router.get("/seasonal")
async def price_seasonal(
    year: int = Query(None, description="目标年份"),
    node_name: str = None,
    price_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(NodePrice)
    if node_name:
        query = query.where(NodePrice.node_name == node_name)
    if price_type:
        query = query.where(NodePrice.price_type == price_type)
    if year:
        query = query.where(
            func.extract("year", NodePrice.trade_date) == year
        )
    query = query.order_by(NodePrice.trade_date)

    rows = await db.execute(query)
    items = rows.scalars().all()

    monthly = {}
    for r in items:
        month_key = r.trade_date.strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {"vals": []}
        if r.slots:
            monthly[month_key]["vals"].extend(float(v) for v in r.slots.values())

    result = []
    for m_key in sorted(monthly.keys()):
        vals = monthly[m_key]["vals"]
        if not vals:
            continue
        result.append({
            "month": m_key,
            "avg_price": round(sum(vals) / len(vals), 2),
            "max_price": round(max(vals), 2),
            "min_price": round(min(vals), 2),
        })

    # 按月份分组（跨年同月对比）
    month_groups = {}
    for r in result:
        m = r["month"][5:7]
        if m not in month_groups:
            month_groups[m] = []
        month_groups[m].append(r)

    by_month = {}
    for m, items in sorted(month_groups.items()):
        by_month[m] = sorted(items, key=lambda x: x["month"])

    available_years = sorted(set(
        r.trade_date.year for r in items
    ))

    return {
        "year": year,
        "node_name": node_name,
        "price_type": price_type,
        "monthly": result,
        "by_month": by_month,
        "available_years": available_years,
    }


# ─── 价格与负荷/天气关联分析 ──────────────────────────
@router.get("/correlation")
async def price_correlation(
    date_from: str = Query(...),
    date_to: str = Query(...),
    node_name: str = None,
    db: AsyncSession = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    # 获取价格数据
    price_query = select(NodePrice).where(NodePrice.trade_date.between(d_from, d_to))
    if node_name:
        price_query = price_query.where(NodePrice.node_name == node_name)
    price_rows = await db.execute(price_query)
    price_items = price_rows.scalars().all()

    # 获取负荷数据
    load_rows = await db.execute(
        select(LoadData.record_date, LoadData.slots)
        .where(LoadData.record_date.between(d_from, d_to))
    )

    # 获取天气数据
    weather_rows = await db.execute(
        select(WeatherData.record_date, WeatherData.temperature)
        .where(WeatherData.record_date.between(d_from, d_to))
        .where(WeatherData.data_type == "日均温")
    )

    # 按日聚合价格
    daily_price = {}
    for r in price_items:
        key = str(r.trade_date)
        if key not in daily_price:
            daily_price[key] = []
        if r.slots:
            daily_price[key].extend(float(v) for v in r.slots.values())

    # 按日聚合负荷
    daily_load = {}
    for r in load_rows.fetchall():
        if r.slots:
            vals = [float(v) for v in r.slots.values() if v is not None]
            if vals:
                daily_load[str(r[0])] = sum(vals) / len(vals)

    # 按日聚合天气
    daily_weather = {}
    for r in weather_rows.fetchall():
        k = str(r[0])
        if r.temperature is not None:
            if k not in daily_weather:
                daily_weather[k] = []
            daily_weather[k].append(float(r.temperature))

    # 合并数据
    points = []
    all_dates = sorted(set(list(daily_price.keys()) + list(daily_load.keys()) + list(daily_weather.keys())))
    for d in all_dates:
        p = {"date": d}
        if d in daily_price and daily_price[d]:
            vals = daily_price[d]
            p["avg_price"] = round(sum(vals) / len(vals), 2)
        if d in daily_load:
            p["avg_load"] = round(daily_load[d], 2)
        if d in daily_weather and daily_weather[d]:
            p["avg_temp"] = round(sum(daily_weather[d]) / len(daily_weather[d]), 2)
        if len(p) > 1:
            points.append(p)

    # 计算相关系数
    price_vals = [p["avg_price"] for p in points if "avg_price" in p and "avg_load" in p]
    load_vals = [p["avg_load"] for p in points if "avg_price" in p and "avg_load" in p]
    temp_vals = [p["avg_temp"] for p in points if "avg_price" in p and "avg_temp" in p]
    price_for_temp = [p["avg_price"] for p in points if "avg_price" in p and "avg_temp" in p]

    def pearson(x, y):
        n = len(x)
        if n < 2:
            return None
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        den = math.sqrt(sum((xi - mx) ** 2 for xi in x)) * math.sqrt(sum((yi - my) ** 2 for yi in y))
        return round(num / den, 4) if den != 0 else 0

    return {
        "date_from": date_from,
        "date_to": date_to,
        "node_name": node_name,
        "points": points,
        "correlation": {
            "price_vs_load": pearson(price_vals, load_vals),
            "price_vs_temperature": pearson(price_for_temp, temp_vals),
        },
    }

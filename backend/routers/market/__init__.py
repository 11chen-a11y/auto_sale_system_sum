# 公开市场数据模块包
# 节点电价、负荷数据、天气数据、价格趋势：所有登录用户可读，写操作在各自路由中单独校验管理员权限

from fastapi import APIRouter

from .load_data import router as load_data_router
from .node_price import router as node_price_router
from .price_trend import router as price_trend_router
from .weather import router as weather_router

market_router = APIRouter()
market_router.include_router(load_data_router)
market_router.include_router(node_price_router)
market_router.include_router(price_trend_router)
market_router.include_router(weather_router)

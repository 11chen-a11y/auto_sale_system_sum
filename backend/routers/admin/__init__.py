# 管理员功能模块包
# 除用户模块和公开市场数据模块外的业务模块统一放在本包中，仅在 main.py 挂载时加上 require_admin 权限校验

from fastapi import APIRouter

from .analysis import router as analysis_router
from .bill import router as bill_router
from .contract import router as contract_router
from .customer import router as customer_router
from .generator import router as generator_router
from .load_forecast import router as load_forecast_router
from .new_energy import router as new_energy_router
from .power_bid import router as power_bid_router
from .settlement import router as settlement_router
from .spot_trade import router as spot_trade_router

# 聚合为一个路由，main.py 只需挂载一次并统一加管理员权限
admin_router = APIRouter()
admin_router.include_router(analysis_router)
admin_router.include_router(bill_router)
admin_router.include_router(contract_router)
admin_router.include_router(customer_router)
admin_router.include_router(generator_router)
admin_router.include_router(load_forecast_router)
admin_router.include_router(new_energy_router)
admin_router.include_router(power_bid_router)
admin_router.include_router(settlement_router)
admin_router.include_router(spot_trade_router)

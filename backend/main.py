# 售电管理系统入口
# 挂载路由、配置 CORS、启动时自动建表、关闭 Redis

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from config.conf_db import engine, Base
from utils.redis import close_redis
from utils.auth import require_admin, get_current_user
from utils.logger import setup_logging, get_logger
from routers.users import router as users_router
from routers.admin import admin_router
from routers.market import market_router

setup_logging()
logger = get_logger(__name__)


# 合并数据库和 Redis 生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    try:
        await close_redis()
    except Exception as exc:
        logger.warning("关闭 Redis 连接时出错: %s", exc)
    await engine.dispose()


app = FastAPI(title="售电管理系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 全局异常处理 ─────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("参数校验失败 %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": "请求参数校验失败", "errors": exc.errors()},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning("参数解析错误 %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=400, content={"detail": f"参数格式错误: {exc}"})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error("服务错误 %s %s: %s", request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


# 数据库连接类错误（连接中断/超时/宕机等）统一降级为 503，避免误导性 500
@app.exception_handler(OperationalError)
async def db_operational_error_handler(request: Request, exc: OperationalError):
    logger.error("数据库连接异常 %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=503, content={"detail": "数据库暂不可用，请稍后重试"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常 %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})


app.include_router(users_router)
# 公开市场数据：登录即可读取（节点电价/负荷/天气/价格趋势），写操作已按接口单独校验管理员
app.include_router(market_router, dependencies=[Depends(get_current_user)])
# 其余业务功能模块统一挂载，并强制要求管理员权限
app.include_router(admin_router, dependencies=[Depends(require_admin)])


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)


@app.get("/")
async def root():
    return {"message": "售电管理系统 API"}

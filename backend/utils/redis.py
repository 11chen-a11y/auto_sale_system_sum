# 验证码存取工具函数
# 封装 Redis 异常，Redis 不可用时返回业务错误而不是裸 500

from typing import Optional

from fastapi import HTTPException

import redis.exceptions as redis_exc
from config.conf_redis import redis_client, CODE_TTL
from utils.logger import get_logger

logger = get_logger(__name__)

_REDIS_ERR_MSG = "验证码/短信服务暂时不可用，请稍后重试"


# 存验证码
async def save_code(phone: str, code: str):
    try:
        await redis_client.set(f"sms:{phone}", code, ex=CODE_TTL)
    except (redis_exc.ConnectionError, redis_exc.TimeoutError, OSError) as exc:
        logger.error("Redis 写入失败 phone=%s: %s", phone, exc)
        raise HTTPException(status_code=503, detail=_REDIS_ERR_MSG)


# 取验证码
async def get_code(phone: str) -> Optional[str]:
    try:
        return await redis_client.get(f"sms:{phone}")
    except (redis_exc.ConnectionError, redis_exc.TimeoutError, OSError) as exc:
        logger.error("Redis 读取失败 phone=%s: %s", phone, exc)
        raise HTTPException(status_code=503, detail=_REDIS_ERR_MSG)


# 删验证码（验证成功后调用）
async def delete_code(phone: str):
    try:
        await redis_client.delete(f"sms:{phone}")
    except (redis_exc.ConnectionError, redis_exc.TimeoutError, OSError) as exc:
        logger.error("Redis 删除失败 phone=%s: %s", phone, exc)
        raise HTTPException(status_code=503, detail=_REDIS_ERR_MSG)


# 关闭连接
async def close_redis():
    try:
        await redis_client.close()
    except Exception as exc:
        logger.warning("关闭 Redis 连接时出错: %s", exc)
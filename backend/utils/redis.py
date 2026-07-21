# 验证码存取工具函数

from typing import Optional

from config.conf_redis import redis_client, CODE_TTL


# 存验证码
async def save_code(phone: str, code: str):
    await redis_client.set(f"sms:{phone}", code, ex=CODE_TTL)


# 取验证码
async def get_code(phone: str) -> Optional[str]:
    return await redis_client.get(f"sms:{phone}")


# 删验证码（验证成功后调用）
async def delete_code(phone: str):
    await redis_client.delete(f"sms:{phone}")


# 关闭连接
async def close_redis():
    await redis_client.close()

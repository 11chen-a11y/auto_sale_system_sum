# Redis 连接配置

import redis.asyncio as redis

REDIS_URL = "redis://127.0.0.1:6379/0"
CODE_TTL = 300  # 验证码过期时间（秒）

redis_client = redis.from_url(REDIS_URL, decode_responses=True, protocol=2)

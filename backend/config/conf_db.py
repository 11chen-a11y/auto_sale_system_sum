from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase


engine = create_async_engine(
    'mysql+aiomysql://root:123456@127.0.0.1:3306/auto_sale_system',
    echo=True,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=20,
    max_overflow=20
)

session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


# 所有模型的基类
class Base(DeclarativeBase):
    pass


# 依赖注入：获取数据库会话
async def get_db() -> AsyncSession:
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()



from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import Generator
from schemas.schemas import GeneratorCreate, GeneratorUpdate, GeneratorOut, GeneratorList
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/generator", tags=["发电商管理"])


@router.get("/types")
async def get_generator_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Generator.generator_type).distinct().where(Generator.generator_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/list", response_model=GeneratorList)
async def list_generators(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    generator_name: str = None,
    generator_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Generator)
    count_query = select(func.count(Generator.generator_id))

    if generator_name:
        pattern = f"%{generator_name}%"
        query = query.where(Generator.generator_name.like(pattern))
        count_query = count_query.where(Generator.generator_name.like(pattern))
    if generator_type:
        query = query.where(Generator.generator_type == generator_type)
        count_query = count_query.where(Generator.generator_type == generator_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Generator.generator_id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/all")
async def get_all_generators(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Generator.generator_id, Generator.generator_name).order_by(Generator.generator_name))
    return [{"generator_id": r[0], "generator_name": r[1]} for r in result.fetchall()]


@router.post("/create", response_model=GeneratorOut)
async def create_generator(data: GeneratorCreate, db: AsyncSession = Depends(get_db)):
    record = Generator(**data.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{generator_id}", response_model=GeneratorOut)
async def update_generator(generator_id: int, data: GeneratorUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Generator).where(Generator.generator_id == generator_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(record, k, v)

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{generator_id}")
async def delete_generator(generator_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Generator).where(Generator.generator_id == generator_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_generators(
    generator_name: str = None,
    generator_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Generator)
    if generator_name:
        query = query.where(Generator.generator_name.like(f"%{generator_name}%"))
    if generator_type:
        query = query.where(Generator.generator_type == generator_type)
    query = query.order_by(Generator.generator_id.desc())
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("发电商ID", "generator_id"),
            ("名称", "generator_name"),
            ("类型", "generator_type"),
            ("装机容量(MW)", "capacity"),
            ("所在地", "location"),
            ("联系人", "contact_person"),
            ("联系电话", "contact_phone"),
            ("状态", "status"),
            ("创建时间", "created_at"),
            ("更新时间", "updated_at"),
        ],
        "generator_export.csv",
    )


@router.post("/batch")
async def batch_create(data: list[GeneratorCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")
    try:
        records = [Generator(**item.model_dump()) for item in data]
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入发电商失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效或重复数据，请检查后重试")
    return {"msg": f"成功导入 {len(records)} 条"}

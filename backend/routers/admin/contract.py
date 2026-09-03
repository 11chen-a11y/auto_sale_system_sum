from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from models.models import Contract
from schemas.schemas import ContractCreate, ContractUpdate, ContractOut, ContractList
from utils.csv_export import csv_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/contract", tags=["合约管理"])


@router.get("/types")
async def get_contract_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contract.contract_type).distinct().where(Contract.contract_type.isnot(None)))
    return [row[0] for row in result.fetchall()]


@router.get("/list", response_model=ContractList)
async def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    contract_type: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Contract)
    count_query = select(func.count(Contract.contract_id))

    if contract_type:
        query = query.where(Contract.contract_type == contract_type)
        count_query = count_query.where(Contract.contract_type == contract_type)
    if status:
        query = query.where(Contract.status == status)
        count_query = count_query.where(Contract.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Contract.start_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/create", response_model=ContractOut)
async def create_contract(data: ContractCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Contract).where(Contract.contract_no == data.contract_no))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="合同编号已存在")

    record = Contract(
        contract_no=data.contract_no,
        contract_type=data.contract_type,
        party_a=data.party_a,
        party_b=data.party_b,
        generator_id=data.generator_id,
        customer_id=data.customer_id,
        start_date=date.fromisoformat(data.start_date),
        end_date=date.fromisoformat(data.end_date),
        contracted_volume=data.contracted_volume,
        contract_price=data.contract_price,
        delivery_point=data.delivery_point,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/update/{contract_id}", response_model=ContractOut)
async def update_contract(contract_id: int, data: ContractUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contract).where(Contract.contract_id == contract_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.contract_price is not None:
        record.contract_price = data.contract_price
    if data.contracted_volume is not None:
        record.contracted_volume = data.contracted_volume
    if data.delivery_point is not None:
        record.delivery_point = data.delivery_point
    if data.status is not None:
        record.status = data.status

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/delete/{contract_id}")
async def delete_contract(contract_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contract).where(Contract.contract_id == contract_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"msg": "删除成功"}


@router.get("/export")
async def export_contracts(
    contract_type: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Contract)
    if contract_type:
        query = query.where(Contract.contract_type == contract_type)
    if status:
        query = query.where(Contract.status == status)
    query = query.order_by(Contract.start_date.desc())
    rows = (await db.execute(query)).scalars().all()
    return csv_response(
        rows,
        [
            ("合约ID", "contract_id"),
            ("合同编号", "contract_no"),
            ("合约类型", "contract_type"),
            ("甲方", "party_a"),
            ("乙方", "party_b"),
            ("发电商ID", "generator_id"),
            ("客户ID", "customer_id"),
            ("开始日期", "start_date"),
            ("结束日期", "end_date"),
            ("合同电量(MWh)", "contracted_volume"),
            ("合同电价(元/MWh)", "contract_price"),
            ("交割点", "delivery_point"),
            ("状态", "status"),
            ("创建时间", "created_at"),
            ("更新时间", "updated_at"),
        ],
        "contract_export.csv",
    )


@router.post("/batch")
async def batch_create(data: list[ContractCreate], db: AsyncSession = Depends(get_db)):
    if not data:
        raise HTTPException(status_code=400, detail="导入数据为空")
    try:
        records = [Contract(**item.model_dump()) for item in data]
        db.add_all(records)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("批量导入合约失败: %s", exc)
        raise HTTPException(status_code=400, detail="导入失败：存在无效或重复数据，请检查后重试")
    return {"msg": f"成功导入 {len(records)} 条"}

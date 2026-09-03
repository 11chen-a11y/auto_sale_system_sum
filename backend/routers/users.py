# 用户相关 API 接口
# 注册、登录、发送验证码、手机号登录

import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.conf_db import get_db
from utils.redis import save_code, get_code, delete_code
from models.models import SysUser, Customer
from schemas.schemas import UserCreate, UserLogin, UserOut, TokenWithUser, SendCode, PhoneLogin, DeleteAccount, RoleUpdate
from utils.auth import hash_password, verify_password, create_access_token, get_current_user, require_admin
from utils.logger import get_logger
import httpx

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["用户管理"])


# 发送验证码（spug 短信推送）


@router.post("/send-code")
async def send_code(data: SendCode):
    code = str(random.randint(100000, 999999))
    await save_code(data.phone, code)  # redis缓存保存验证码

    sms_url = "https://push.spug.cc/sms/El-0VaSvRPK1R3VYz7uvMQ"
    body = {"code": code, "number": "5", "to": data.phone}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(sms_url, json=body)
    except httpx.HTTPError as exc:
        logger.error("短信推送请求失败 phone=%s: %s", data.phone, exc)
        raise HTTPException(status_code=500, detail="短信发送失败")

    if resp.status_code != 200:
        logger.error("短信推送响应异常 phone=%s 状态码=%s 响应=%s", data.phone, resp.status_code, resp.text)
        raise HTTPException(status_code=500, detail="短信发送失败")

    return {"msg": "验证码已发送"}


# 注册（用户名 + 手机号 + 密码 + 验证码）
@router.post("/register", response_model=UserOut)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    saved_code = await get_code(data.phone)  # 验证码校验
    if not saved_code or saved_code != data.code:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    await delete_code(data.phone)  # 验证码通过后删除

    # 用户名唯一校验
    result = await db.execute(select(SysUser).where(SysUser.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 手机号唯一校验
    result = await db.execute(select(SysUser).where(SysUser.phone == data.phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该手机号已注册")

    # 库中没有任何管理员时，新注册的用户自动成为管理员，用于初始化管理员账号
    admin_count = (await db.execute(
        select(func.count(SysUser.user_id)).where(SysUser.role == "admin")
    )).scalar_one()
    role = "admin" if admin_count == 0 else "viewer"

    user = SysUser(
        username=data.username,
        phone=data.phone,
        phone_verified=True,
        password_hash=hash_password(data.password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# 用户名+密码登录
@router.post("/login", response_model=TokenWithUser)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SysUser).where(SysUser.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "user": user}


# 手机号+验证码登录
@router.post("/login-phone", response_model=TokenWithUser)
async def login_phone(data: PhoneLogin, db: AsyncSession = Depends(get_db)):
    saved_code = await get_code(data.phone)
    if not saved_code or saved_code != data.code:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    await delete_code(data.phone)  # 验证码通过后删除

    result = await db.execute(select(SysUser).where(SysUser.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="该手机号未注册")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "user": user}


# 注销账号
@router.delete("/account")
async def delete_account(
    data: DeleteAccount,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")

    await db.execute(
        Customer.__table__.update()
        .where(Customer.user_id == current_user.user_id)
        .values(user_id=None)
    )

    await db.delete(current_user)
    await db.commit()
    return {"msg": "账号已注销"}


@router.get("/home", response_model=UserOut)
async def home(current_user: SysUser = Depends(get_current_user)):
    return current_user


# 用户列表（仅管理员）
@router.get("", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), admin: SysUser = Depends(require_admin)):
    result = await db.execute(select(SysUser).order_by(SysUser.user_id))
    return result.scalars().all()


# 设置用户角色（仅管理员，admin / viewer）
@router.put("/{user_id}/role", response_model=UserOut)
async def set_user_role(
    user_id: int,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: SysUser = Depends(require_admin),
):
    if data.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="角色只能是 admin 或 viewer")

    result = await db.execute(select(SysUser).where(SysUser.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 防止取消最后一个管理员的权限
    if user.role == "admin" and data.role == "viewer":
        admin_count = (await db.execute(select(func.count(SysUser.user_id)).where(SysUser.role == "admin"))).scalar_one()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="至少保留一名管理员")

    user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user


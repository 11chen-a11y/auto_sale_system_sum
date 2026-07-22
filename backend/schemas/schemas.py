# Pydantic 数据模型
# 定义 API 请求和响应的数据结构

from typing import Optional
from pydantic import BaseModel


# 用户注册请求体（含手机号和验证码）
class UserCreate(BaseModel):
    username: str
    phone: str
    password: str
    code: str


# 发送验证码请求体
class SendCode(BaseModel):
    phone: str


# 手机号+验证码登录请求体
class PhoneLogin(BaseModel):
    phone: str
    code: str


# 用户登录请求体
class UserLogin(BaseModel):
    username: str
    password: str


# 用户信息响应体（不含密码）
class UserOut(BaseModel):
    user_id: int
    username: str
    real_name: Optional[str] = None
    role: str

    model_config = {"from_attributes": True}


# JWT Token 响应体
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# 登录响应体（Token + 用户信息）
class TokenWithUser(Token):
    user: UserOut


# 注销账号请求体
class DeleteAccount(BaseModel):
    password: str

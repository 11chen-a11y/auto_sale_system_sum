# Pydantic 数据模型
# 定义 API 请求和响应的数据结构
from datetime import date, datetime
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


# 设置用户角色请求体
class RoleUpdate(BaseModel):
    role: str


# ─── 新能源出力 ─────────────────────────────────────────────
class NewEnergyBase(BaseModel):
    record_date: str
    station_name: str
    energy_type: Optional[str] = None
    forecast_slots: Optional[dict] = None
    actual_slots: Optional[dict] = None


class NewEnergyCreate(NewEnergyBase):
    pass


class NewEnergyUpdate(BaseModel):
    record_date: Optional[str] = None
    station_name: Optional[str] = None
    energy_type: Optional[str] = None
    forecast_slots: Optional[dict] = None
    actual_slots: Optional[dict] = None


class NewEnergyOut(NewEnergyBase):
    energy_id: int
    record_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class NewEnergyList(BaseModel):
    items: list[NewEnergyOut]
    total: int
    page: int
    page_size: int


# ─── 节点电价 ─────────────────────────────────────────────
class NodePriceCreate(BaseModel):
    trade_date: str
    node_name: str
    price_type: Optional[str] = None
    slots: Optional[dict] = None


class NodePriceUpdate(BaseModel):
    price_type: Optional[str] = None
    slots: Optional[dict] = None


class NodePriceOut(BaseModel):
    price_id: int
    trade_date: date
    node_name: str
    price_type: Optional[str] = None
    slots: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NodePriceList(BaseModel):
    items: list[NodePriceOut]
    total: int
    page: int
    page_size: int


# ─── 实际负荷 ─────────────────────────────────────────────
class LoadDataBase(BaseModel):
    customer_id: Optional[int] = None
    record_date: str
    data_type: str = "实际负荷"
    slots: Optional[dict] = None
    total_kwh: Optional[float] = None
    remarks: Optional[str] = None


class LoadDataCreate(LoadDataBase):
    pass


class LoadDataUpdate(BaseModel):
    customer_id: Optional[int] = None
    record_date: Optional[str] = None
    data_type: Optional[str] = None
    slots: Optional[dict] = None
    total_kwh: Optional[float] = None
    remarks: Optional[str] = None


class LoadDataOut(LoadDataBase):
    load_id: int
    record_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class LoadDataList(BaseModel):
    items: list[LoadDataOut]
    total: int
    page: int
    page_size: int


# ─── 现货交易 ─────────────────────────────────────────────
class SpotTradeBase(BaseModel):
    trade_month: str
    trade_type: Optional[str] = None
    avg_price: Optional[float] = None
    volume: Optional[float] = None


class SpotTradeCreate(SpotTradeBase):
    pass


class SpotTradeUpdate(BaseModel):
    trade_month: Optional[str] = None
    trade_type: Optional[str] = None
    avg_price: Optional[float] = None
    volume: Optional[float] = None


class SpotTradeOut(SpotTradeBase):
    trade_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SpotTradeList(BaseModel):
    items: list[SpotTradeOut]
    total: int
    page: int
    page_size: int


# ─── 天气数据 ─────────────────────────────────────────────
class WeatherBase(BaseModel):
    station_name: Optional[str] = None
    city: Optional[str] = None
    record_date: str
    data_type: Optional[str] = None
    temperature: Optional[float] = None


class WeatherCreate(WeatherBase):
    pass


class WeatherUpdate(BaseModel):
    station_name: Optional[str] = None
    city: Optional[str] = None
    record_date: Optional[str] = None
    data_type: Optional[str] = None
    temperature: Optional[float] = None


class WeatherOut(WeatherBase):
    weather_id: int
    record_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class WeatherList(BaseModel):
    items: list[WeatherOut]
    total: int
    page: int
    page_size: int


# ─── 客户档案 ─────────────────────────────────────────────
class CustomerBase(BaseModel):
    customer_name: str
    customer_type: Optional[str] = None
    voltage_level: Optional[str] = None
    contract_cap: Optional[float] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_type: Optional[str] = None
    voltage_level: Optional[str] = None
    contract_cap: Optional[float] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class CustomerOut(CustomerBase):
    customer_id: int
    status: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerList(BaseModel):
    items: list[CustomerOut]
    total: int
    page: int
    page_size: int


# ─── 账单管理 ─────────────────────────────────────────────
class BillBase(BaseModel):
    customer_id: int
    bill_month: str
    total_kwh: Optional[float] = None
    total_amount: Optional[float] = None
    payment_status: str = "未付"
    due_date: Optional[str] = None


class BillCreate(BillBase):
    pass


class BillUpdate(BaseModel):
    total_kwh: Optional[float] = None
    total_amount: Optional[float] = None
    payment_status: Optional[str] = None
    due_date: Optional[str] = None


class BillOut(BillBase):
    bill_id: int
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BillList(BaseModel):
    items: list[BillOut]
    total: int
    page: int
    page_size: int


# ─── 发电商管理 ─────────────────────────────────────────────
class GeneratorBase(BaseModel):
    generator_name: str
    generator_type: Optional[str] = None
    capacity: Optional[float] = None
    location: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None


class GeneratorCreate(GeneratorBase):
    pass


class GeneratorUpdate(BaseModel):
    generator_name: Optional[str] = None
    generator_type: Optional[str] = None
    capacity: Optional[float] = None
    location: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    status: Optional[int] = None


class GeneratorOut(GeneratorBase):
    generator_id: int
    status: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GeneratorList(BaseModel):
    items: list[GeneratorOut]
    total: int
    page: int
    page_size: int


# ─── 报价/竞价 ─────────────────────────────────────────────
class PowerBidBase(BaseModel):
    generator_id: Optional[int] = None
    bid_date: str
    bid_type: str
    price: Optional[float] = None
    volume: Optional[float] = None


class PowerBidCreate(PowerBidBase):
    pass


class PowerBidUpdate(BaseModel):
    price: Optional[float] = None
    volume: Optional[float] = None
    status: Optional[str] = None


class PowerBidOut(PowerBidBase):
    bid_id: int
    cleared_price: Optional[float] = None
    cleared_volume: Optional[float] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PowerBidList(BaseModel):
    items: list[PowerBidOut]
    total: int
    page: int
    page_size: int


# ─── 合约管理 ─────────────────────────────────────────────
class ContractBase(BaseModel):
    contract_no: str
    contract_type: str
    party_a: str
    party_b: str
    generator_id: Optional[int] = None
    customer_id: Optional[int] = None
    start_date: str
    end_date: str
    contracted_volume: Optional[float] = None
    contract_price: Optional[float] = None
    delivery_point: Optional[str] = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    contract_price: Optional[float] = None
    contracted_volume: Optional[float] = None
    delivery_point: Optional[str] = None
    status: Optional[str] = None


class ContractOut(ContractBase):
    contract_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractList(BaseModel):
    items: list[ContractOut]
    total: int
    page: int
    page_size: int


# ─── 交易结算 ─────────────────────────────────────────────
class SettlementBase(BaseModel):
    contract_id: Optional[int] = None
    settle_month: str
    settle_type: str
    volume: Optional[float] = None
    price: Optional[float] = None
    amount: Optional[float] = None


class SettlementCreate(SettlementBase):
    pass


class SettlementUpdate(BaseModel):
    volume: Optional[float] = None
    amount: Optional[float] = None
    status: Optional[str] = None


class SettlementOut(SettlementBase):
    settlement_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettlementList(BaseModel):
    items: list[SettlementOut]
    total: int
    page: int
    page_size: int

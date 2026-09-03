# 数据库模型定义（SQLAlchemy 2.0 新风格）
# 8 张表，时段数据用 JSON 存储（96 个 15 分钟间隔）

from datetime import datetime
from typing import List, Optional
from sqlalchemy import BigInteger, String, Date, DateTime, DECIMAL, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.conf_db import Base


# 用户表
class SysUser(Base):
    __tablename__ = "sys_user"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[Optional[str]] = mapped_column(String(50))
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    phone_verified: Mapped[bool] = mapped_column(default=False)
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    status: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    customers: Mapped[List["Customer"]] = relationship(back_populates="user")


# 客户档案
class Customer(Base):
    __tablename__ = "customer"
    customer_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_type: Mapped[Optional[str]] = mapped_column(String(20))
    voltage_level: Mapped[Optional[str]] = mapped_column(String(20))
    contract_cap: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2))
    address: Mapped[Optional[str]] = mapped_column(String(200))
    contact_name: Mapped[Optional[str]] = mapped_column(String(50))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sys_user.user_id"))
    status: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    user: Mapped[Optional["SysUser"]] = relationship(back_populates="customers")
    bills: Mapped[List["Bill"]] = relationship(back_populates="customer")


# 节点电价
class NodePrice(Base):
    __tablename__ = "node_price"
    price_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_type: Mapped[Optional[str]] = mapped_column(String(20))
    slots: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint("trade_date", "node_name", name="uq_node_price"),)


# 实际负荷
class LoadData(Base):
    __tablename__ = "load_data"
    load_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customer.customer_id"), index=True)
    record_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    data_type: Mapped[str] = mapped_column(String(20), default="实际负荷")
    slots: Mapped[Optional[dict]] = mapped_column(JSON)
    total_kwh: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    remarks: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    customer: Mapped[Optional["Customer"]] = relationship()

    __table_args__ = (UniqueConstraint("customer_id", "record_date", "data_type", name="uq_load_data"),)


# 新能源出力
class NewEnergy(Base):
    __tablename__ = "new_energy"
    energy_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    station_name: Mapped[str] = mapped_column(String(100), nullable=False)
    energy_type: Mapped[Optional[str]] = mapped_column(String(20))
    forecast_slots: Mapped[Optional[dict]] = mapped_column(JSON)
    actual_slots: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint("record_date", "station_name", name="uq_new_energy"),)


# 现货交易
class SpotTrade(Base):
    __tablename__ = "spot_trade"
    trade_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_month: Mapped[str] = mapped_column(String(7), nullable=False)
    trade_type: Mapped[Optional[str]] = mapped_column(String(20))
    avg_price: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2))
    volume: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint("trade_month", "trade_type", name="uq_spot_trade"),)


# 天气数据
class WeatherData(Base):
    __tablename__ = "weather_data"
    weather_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    station_name: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(50))
    record_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    data_type: Mapped[Optional[str]] = mapped_column(String(20))
    temperature: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint("station_name", "record_date", "data_type", name="uq_weather_data"),)


# 账单
class Bill(Base):
    __tablename__ = "bill"
    bill_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.customer_id"), nullable=False, index=True)
    bill_month: Mapped[str] = mapped_column(String(7), nullable=False)
    total_kwh: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    total_amount: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    payment_status: Mapped[str] = mapped_column(String(20), default="未付")
    due_date: Mapped[Optional[datetime]] = mapped_column(Date)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    customer: Mapped["Customer"] = relationship(back_populates="bills")

    __table_args__ = (UniqueConstraint("customer_id", "bill_month", name="uq_bill"),)


# 发电商
class Generator(Base):
    __tablename__ = "generator"
    generator_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    generator_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    generator_type: Mapped[Optional[str]] = mapped_column(String(20))
    capacity: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    contact_person: Mapped[Optional[str]] = mapped_column(String(50))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20))
    status: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


# 报价/竞价
class PowerBid(Base):
    __tablename__ = "power_bid"
    bid_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    generator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("generator.generator_id"), index=True)
    bid_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    bid_type: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2))
    volume: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    cleared_price: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2))
    cleared_volume: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    status: Mapped[str] = mapped_column(String(20), default="待出清")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    generator: Mapped[Optional["Generator"]] = relationship()


# 合约管理
class Contract(Base):
    __tablename__ = "contract"
    contract_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contract_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    contract_type: Mapped[str] = mapped_column(String(20), nullable=False)
    party_a: Mapped[str] = mapped_column(String(100), nullable=False)
    party_b: Mapped[str] = mapped_column(String(100), nullable=False)
    generator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("generator.generator_id"), index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customer.customer_id"), index=True)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    contracted_volume: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    contract_price: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2))
    delivery_point: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="执行中")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    generator: Mapped[Optional["Generator"]] = relationship()
    customer: Mapped[Optional["Customer"]] = relationship()


# 交易结算
class Settlement(Base):
    __tablename__ = "settlement"
    settlement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contract.contract_id"), index=True)
    settle_month: Mapped[str] = mapped_column(String(7), nullable=False)
    settle_type: Mapped[str] = mapped_column(String(20), nullable=False)
    volume: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    price: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2))
    amount: Mapped[Optional[float]] = mapped_column(DECIMAL(14, 2))
    status: Mapped[str] = mapped_column(String(20), default="待确认")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    contract: Mapped[Optional["Contract"]] = relationship()

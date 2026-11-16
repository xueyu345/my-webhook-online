from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def now_utc():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    endpoints = relationship("Endpoint", back_populates="owner", cascade="all, delete-orphan")

class Endpoint(Base):
    __tablename__ = "endpoints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    response_code: Mapped[int] = mapped_column(Integer, default=200)
    response_body: Mapped[str] = mapped_column(Text, default='{"ok":true}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    owner = relationship("User", back_populates="endpoints")
    logs = relationship("RequestLog", back_populates="endpoint", cascade="all, delete-orphan")

class RequestLog(Base):
    __tablename__ = "request_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id"), index=True)
    method: Mapped[str] = mapped_column(String(12))
    path: Mapped[str] = mapped_column(String(2048))
    query_string: Mapped[str] = mapped_column(Text, default="")
    headers: Mapped[dict] = mapped_column(JSON)
    body: Mapped[str] = mapped_column(Text, default="")
    client_ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    endpoint = relationship("Endpoint", back_populates="logs")

Index("ix_request_logs_endpoint_created", RequestLog.endpoint_id, RequestLog.created_at)

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="staff")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    event_date: Mapped[str] = mapped_column(String(20))
    start_time: Mapped[str] = mapped_column(String(10), default="08:00")
    end_time: Mapped[str] = mapped_column(String(10), default="17:00")
    location: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    participants: Mapped[list["Participant"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    company_name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(100), default="General")
    contact_name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    participants: Mapped[list["Participant"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    position: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    qr_token: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    attendance_status: Mapped[str] = mapped_column(String(30), default="not_attended", index=True)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_in_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    checked_in_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event: Mapped[Event] = relationship(back_populates="participants")
    vendor: Mapped[Vendor | None] = relationship(back_populates="participants")


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    participant_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    method: Mapped[str] = mapped_column(String(20), default="qr")
    result: Mapped[str] = mapped_column(String(40))
    scanned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str] = mapped_column(Text, default="")

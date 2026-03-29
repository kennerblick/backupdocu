from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Numeric, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hostname: Mapped[Optional[str]] = mapped_column(String(255))
    type: Mapped[Optional[str]] = mapped_column(String(50), default="physical")
    os: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    sources: Mapped[list["BackupSource"]] = relationship("BackupSource", back_populates="server", cascade="all, delete-orphan")


class BackupTarget(Base):
    __tablename__ = "backup_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    hostname: Mapped[Optional[str]] = mapped_column(String(255))
    path: Mapped[Optional[str]] = mapped_column(Text)
    capacity_tb: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BackupSource(Base):
    __tablename__ = "backup_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    path: Mapped[Optional[str]] = mapped_column(Text)
    size_gb: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    server: Mapped["Server"] = relationship("Server", back_populates="sources")


class BackupMethod(Base):
    __tablename__ = "backup_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("backup_sources.id", ondelete="CASCADE"))
    method_id: Mapped[Optional[int]] = mapped_column(ForeignKey("backup_methods.id"))
    primary_target_id: Mapped[Optional[int]] = mapped_column(ForeignKey("backup_targets.id"))
    tape_target_id: Mapped[Optional[int]] = mapped_column(ForeignKey("backup_targets.id"))
    offsite_target_id: Mapped[Optional[int]] = mapped_column(ForeignKey("backup_targets.id"))
    schedule: Mapped[Optional[str]] = mapped_column(String(200))
    retention: Mapped[Optional[str]] = mapped_column(String(200))
    gfs_policy: Mapped[Optional[str]] = mapped_column(String(200))
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_compressed: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_result: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    source: Mapped["BackupSource"] = relationship("BackupSource", foreign_keys=[source_id])
    method: Mapped[Optional["BackupMethod"]] = relationship("BackupMethod")
    primary_target: Mapped[Optional["BackupTarget"]] = relationship("BackupTarget", foreign_keys=[primary_target_id])
    tape_target: Mapped[Optional["BackupTarget"]] = relationship("BackupTarget", foreign_keys=[tape_target_id])
    offsite_target: Mapped[Optional["BackupTarget"]] = relationship("BackupTarget", foreign_keys=[offsite_target_id])

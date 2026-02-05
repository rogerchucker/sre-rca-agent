from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime
from datetime import datetime, timezone
import uuid

from core.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    environment: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    labels = Column(JSONB, default=dict)
    annotations = Column(JSONB, default=dict)
    raw = Column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    reports = relationship("IncidentReport", back_populates="incident", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceItem", back_populates="incident", cascade="all, delete-orphan")
    hypotheses = relationship("Hypothesis", back_populates="incident", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="incident", cascade="all, delete-orphan")


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.id"), nullable=False)
    incident_summary: Mapped[str] = mapped_column(Text, nullable=False)
    report = Column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    incident = relationship("Incident", back_populates="reports")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    time_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    samples = Column(JSONB, default=list)
    top_signals = Column(JSONB, default=dict)
    pointers = Column(JSONB, default=list)
    tags = Column(JSONB, default=list)

    incident = relationship("Incident", back_populates="evidence_items")


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.id"), primary_key=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    score_breakdown = Column(JSONB, default=dict)
    supporting_evidence_ids = Column(JSONB, default=list)
    contradictions = Column(JSONB, default=list)
    validations = Column(JSONB, default=list)
    is_top: Mapped[bool] = mapped_column(Boolean, default=False)

    incident = relationship("Incident", back_populates="hypotheses")


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str] = mapped_column(String, nullable=False, default="Low")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    intent: Mapped[str] = mapped_column(String, nullable=False, default="validation")
    payload = Column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    incident = relationship("Incident", back_populates="actions")


class ActionExecution(Base):
    __tablename__ = "action_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.id"), nullable=False)
    action_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    payload = Column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    actor: Mapped[str] = mapped_column(String, nullable=False, default="system")
    action: Mapped[str] = mapped_column(String, nullable=False)
    detail = Column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

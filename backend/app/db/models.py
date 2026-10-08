from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, JSON, Text, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    tier = Column(String, nullable=False)
    country = Column(String, default="AU")
    account_created = Column(String)
    risk_level = Column(String, default="low")


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    product = Column(String)
    amount = Column(Float)
    purchase_date = Column(String)
    status = Column(String)
    delivery_date = Column(String, nullable=True)
    payment_method = Column(String, default="card")
    condition = Column(String, default="unopened")
    category = Column(String, default="physical")


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.id"))
    order_id = Column(String, ForeignKey("orders.id"))
    category = Column(String)
    status = Column(String)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=now)


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    name = Column(String)
    content_hash = Column(String, unique=True)
    trusted = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=now)


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"))
    section = Column(String)
    text = Column(Text)
    embedding = Column(JSON)
    meta = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=now)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(String, primary_key=True)
    task = Column(Text)
    mode = Column(String)
    purpose = Column(String, default="interactive")
    status = Column(String, default="queued")
    state = Column(JSON, default=dict)
    revision = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=now)
    completed_at = Column(DateTime(timezone=True))
    latency = Column(Float, default=0)
    token_usage = Column(JSON, default=dict)
    estimated_cost = Column(Float, nullable=True)


class AgentEvent(Base):
    __tablename__ = "agent_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("agent_runs.id"), index=True)
    event_type = Column(String)
    node = Column(String)
    tool = Column(String, nullable=True)
    input_summary = Column(JSON)
    output_summary = Column(JSON)
    duration = Column(Float)
    timestamp = Column(DateTime(timezone=True), default=now)


class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("agent_runs.id"))
    result = Column(JSON)


class HumanReview(Base):
    __tablename__ = "human_reviews"
    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("agent_runs.id"))
    decision = Column(String)
    edited_answer = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), default=now)


class SupportAction(Base):
    __tablename__ = "support_actions"
    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("agent_runs.id"), unique=True)
    action = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=now)


class EvalBatch(Base):
    __tablename__ = "evaluation_batches"
    id = Column(String, primary_key=True)
    status = Column(String)
    results = Column(JSON, default=list)
    metrics = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=now)

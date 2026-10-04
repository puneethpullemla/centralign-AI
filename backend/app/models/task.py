import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_task = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    target_company = Column(String(100), nullable=True)
    plan = Column(JSON, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    completion_report = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    steps = relationship("ExecutionStep", back_populates="task", cascade="all, delete-orphan", order_by="ExecutionStep.step_number")
    approvals = relationship("Approval", back_populates="task", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="task", cascade="all, delete-orphan")

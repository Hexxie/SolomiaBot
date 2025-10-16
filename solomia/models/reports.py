import uuid
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy import Column, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from solomia.core.db import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reports")
    items = relationship("ReportItem", back_populates="report", cascade="all, delete-orphan")

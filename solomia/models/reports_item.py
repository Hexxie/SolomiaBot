import uuid
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship
from solomia.core.db import Base


class ReportItem(Base):
    __tablename__ = "report_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID, ForeignKey("reports.id", ondelete="CASCADE"))
    category_id = Column(Integer, ForeignKey("food_categories.id", ondelete="SET NULL"))
    product_name = Column(String, nullable=False)
    amount_grams = Column(Float, nullable=True)

    report = relationship("Report", back_populates="items")
    category = relationship("FoodCategory")

import uuid
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from solomia.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    birth_year = Column(Integer, nullable=True)

    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("FoodCategory", secondary="category_to_user", viewonly=True)
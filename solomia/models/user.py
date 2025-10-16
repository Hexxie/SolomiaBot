from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from solomia.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    birth_year = Column(Integer, nullable=True)

    metrics = relationship(
        "UserMetric",
        back_populates="user",
        cascade="all, delete-orphan"
    )
from sqlalchemy import Column, ForeignKey, Float
from solomia.core.db import Base
from sqlalchemy.orm import relationship

class CategoryToUser(Base):
    __tablename__ = "category_to_user"

    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(ForeignKey("food_categories.id", ondelete="CASCADE"), primary_key=True)
    amount_grams = Column(Float, nullable=True)

    user = relationship("User")
    category = relationship("FoodCategory", back_populates="user_links")



from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import UserDefinedType

from solomia.core.db import Base


class Vector(UserDefinedType):
    def __init__(self, dimensions):
        self.dimensions = dimensions

    def get_col_spec(self):
        return f"vector({self.dimensions})"


class FoodCategory(Base):
    __tablename__ = "food_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    examples = Column(ARRAY(String))
    embedding = Column(Vector(768))
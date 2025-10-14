from typing import Callable
from contextlib import AbstractAsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import numpy as np

from solomia.models.food_category import FoodCategory
from solomia.repository.base_repository import BaseRepository


class FoodCategoryRepository(BaseRepository[FoodCategory]):
    def __init__(self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]):
        super().__init__(session_factory, FoodCategory)

    async def get_id_by_name(self, category_name: str) -> int | None:
        """Return category id by its name."""
        async with self.session_factory() as session:
            res = await session.execute(
                text("SELECT id FROM food_categories WHERE name = :name"),
                {"name": category_name.strip()},
            )
            row = res.first()
            return row[0] if row else None

    async def get_by_example(self, example_name: str):
        async with self.session_factory() as session:
            res = await session.execute(
                text("SELECT id, name FROM food_categories WHERE :pname = ANY(examples)"),
                {"pname": example_name},
            )
            return res.mappings().first()

    async def get_all_with_embeddings(self):
        async with self.session_factory() as session:
            res = await session.execute(
                text("SELECT id, name, examples, embedding FROM food_categories")
            )
            return res.mappings().all()

    async def insert_category(self, name: str, examples: list[str], embedding: np.ndarray):
        emb_str = "[" + ", ".join(str(x) for x in embedding) + "]"
        async with self.session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO food_categories (name, examples, embedding)
                    VALUES (:name, :examples, :embedding)
                """),
                {"name": name, "examples": examples, "embedding": emb_str},
            )
            await session.commit()

    async def append_example(self, category_id: int, new_example: str):
        async with self.session_factory() as session:
            await session.execute(
                text("""
                    UPDATE food_categories
                    SET examples = array_append(examples, :example)
                    WHERE id = :id
                """),
                {"id": category_id, "example": new_example},
            )
            await session.commit()

    async def get_examples_by_id(self, category_id: int) -> list[str]:
        """Return all examples for the given category id."""
        async with self.session_factory() as session:
            res = await session.execute(
                text("SELECT examples FROM food_categories WHERE id = :id"),
                {"id": category_id},
            )
            row = res.first()
            return row[0] if row else []

    async def update_embedding(self, category_id: int, embedding: np.ndarray):
        emb_str = "[" + ", ".join(str(x) for x in embedding) + "]"
        async with self.session_factory() as session:
            await session.execute(
                text("""
                    UPDATE food_categories
                    SET embedding = :embedding
                    WHERE id = :id
                """),
                {"id": category_id, "embedding": emb_str},
            )
            await session.commit()

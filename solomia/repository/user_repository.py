from typing import Callable
from contextlib import AbstractAsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from solomia.models.user import User
from solomia.repository.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]):
        super().__init__(session_factory, User)

    async def insert_user(self, telegram_id: str, name: str, birth_year: int | None = None) -> User:
        """
        Create a new user record.

        Args:
            telegram_id (str): Telegram user ID.
            name (str): User's name.
            birth_year (int | None): Optional birth year.

        Returns:
            User: The created User instance.
        """
        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO users (id, telegram_id, name, birth_year)
                    VALUES (gen_random_uuid(), :telegram_id, :name, :birth_year)
                    RETURNING id, telegram_id, name, birth_year
                """),
                {"telegram_id": telegram_id, "name": name, "birth_year": birth_year},
            )

            row = result.mappings().first()
            await session.commit()

            return User(
                id=row["id"],
                telegram_id=row["telegram_id"],
                name=row["name"],
                birth_year=row["birth_year"],
            )

    async def get_id_by_telegram_id(self, telegram_id: str):
        """
        Fetch user UUID by Telegram ID.

        Args:
            telegram_id (str): Telegram user ID.

        Returns:
            str | None: UUID string if found, otherwise None.
        """
        async with self.session_factory() as session:
            result = await session.execute(
                text("SELECT id FROM users WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id},
            )
            row = result.first()
            return row[0] if row else None

from contextlib import AbstractAsyncContextManager
from typing import Callable, Type, TypeVar, Generic, Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

T = TypeVar("T")

class BaseRepository(Generic[T]):
    """Generic async repository for SQLAlchemy models."""

    def __init__(self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]], model: Type[T]):
        self.session_factory = session_factory
        self.model = model

    async def get_all(self) -> Sequence[T]:
        async with self.session_factory() as session:
            res = await session.execute(select(self.model))
            return res.scalars().all()

    async def get_by_id(self, obj_id: Any) -> T | None:
        async with self.session_factory() as session:
            return await session.get(self.model, obj_id)

    async def add(self, obj: T) -> T:
        async with self.session_factory() as session:
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj

    async def delete(self, obj: T) -> None:
        async with self.session_factory() as session:
            await session.delete(obj)
            await session.commit()

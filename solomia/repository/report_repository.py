from typing import Callable
from contextlib import AbstractAsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from solomia.models.reports import Report
from solomia.repository.base_repository import BaseRepository
from datetime import date


class ReportRepository(BaseRepository[Report]):
    def __init__(self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]):
        super().__init__(session_factory, Report)

    async def insert_report(self, user_id: str, report_date) -> Report:
        """
        Create a new report record for a given user.

        Args:
            user_id (str): UUID of the user.
            report_date (date): Date of the report.

        Returns:
            Report: The created Report instance.
        """
        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO reports (id, user_id, date, created_at)
                    VALUES (gen_random_uuid(), :user_id, :date, NOW())
                    RETURNING id, user_id, date, created_at
                """),
                {"user_id": user_id, "date": report_date},
            )

            row = result.mappings().first()
            await session.commit()

            return Report(
                id=row["id"],
                user_id=row["user_id"],
                date=row["date"],
                created_at=row["created_at"],
            )

    async def get_report_by_date(self, user_id: str, report_date: date) -> Report | None:
        """
        Fetch the report for a given user and date.

        Args:
            user_id (str): UUID of the user.
            report_date (date): Date to fetch.

        Returns:
            Report | None: Report object if found, otherwise None.
        """
        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, user_id, date, created_at
                    FROM reports
                    WHERE user_id = :user_id AND date = :date
                    LIMIT 1
                """),
                {"user_id": user_id, "date": report_date},
            )
            row = result.mappings().first()
            if not row:
                return None

            return Report(
                id=row["id"],
                user_id=row["user_id"],
                date=row["date"],
                created_at=row["created_at"],
            )

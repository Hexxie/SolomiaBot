from typing import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from solomia.models.reports_item import ReportItem
from solomia.repository.base_repository import BaseRepository


class ReportItemRepository(BaseRepository[ReportItem]):
    def __init__(self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]):
        super().__init__(session_factory, ReportItem)

    async def insert_item(
        self,
        report_id: str,
        product_name: str,
        amount_grams: float | None,
        category_id: int | None = None,
    ) -> ReportItem:
        """
        Insert a single report item.

        Args:
            report_id (str): UUID of the report.
            product_name (str): Product name.
            amount_grams (float | None): Product amount in grams.
            category_id (int | None): Optional category ID.

        Returns:
            ReportItem: The created item instance.
        """
        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO report_items (id, report_id, category_id, product_name, amount_grams)
                    VALUES (gen_random_uuid(), :report_id, :category_id, :product_name, :amount_grams)
                    RETURNING id, report_id, category_id, product_name, amount_grams
                """),
                {
                    "report_id": report_id,
                    "category_id": category_id,
                    "product_name": product_name,
                    "amount_grams": amount_grams,
                },
            )

            row = result.mappings().first()
            await session.commit()

            return ReportItem(
                id=row["id"],
                report_id=row["report_id"],
                category_id=row["category_id"],
                product_name=row["product_name"],
                amount_grams=row["amount_grams"],
            )
        
    async def get_items_by_date(self, user_id: str, report_date) -> list[dict]:
      """
      Get all report items for a given user and date.

      Args:
          user_id (str): UUID of the user.
          report_date (date): Date of the report.

      Returns:
          list[dict]: List of items with fields: product_name, amount_grams, category_id.
      """
      async with self.session_factory() as session:
          result = await session.execute(
              text("""
                  SELECT ri.id, ri.product_name, ri.amount_grams, ri.category_id
                  FROM report_items AS ri
                  JOIN reports AS r ON r.id = ri.report_id
                  WHERE r.user_id = :user_id AND r.date = :report_date
                  ORDER BY ri.product_name
              """),
              {"user_id": user_id, "report_date": report_date},
          )
          return result.mappings().all()

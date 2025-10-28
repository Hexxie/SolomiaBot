import asyncio
from solomia.core.db import SessionFactory

from solomia.repository.user_repository import UserRepository
from solomia.repository.category_repository import FoodCategoryRepository
from solomia.models.category_to_user import CategoryToUser

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

async def show_user_plan(session: AsyncSession, telegram_id: str):
    """Показує категорії користувача з вагами"""
    user_repo = UserRepository(SessionFactory)
    user_id = await user_repo.get_id_by_telegram_id(telegram_id)
    if not user_id:
        print("❌ Користувач не знайдений.")
        return None

    # Отримуємо всі категорії
    categories = await session.execute(select(CategoryToUser).where(CategoryToUser.user_id == user_id))
    links = categories.scalars().all()

    if not links:
        print("⚠️ План не сформований.")
    else:
        print(f"\n📋 Поточний план для користувача {telegram_id}:")
        result = await session.execute(
        select(CategoryToUser)
        .options(selectinload(CategoryToUser.category))
        .where(CategoryToUser.user_id == user_id)
    )
    links = result.scalars().all()

    for link in links:
        print(f"{link.category.name}: {link.amount_grams or 0} г")

    return user_id

async def edit_user_plan(session: AsyncSession, user_id):
    """Редагує або додає ваги для всіх категорій"""
    # Отримуємо всі категорії з таблиці FoodCategory
    category_repo = FoodCategoryRepository(SessionFactory)
    categories = await category_repo.get_all()  # очікується list[FoodCategory]

    # Отримуємо поточні значення користувача
    existing = await session.execute(
        select(CategoryToUser).where(CategoryToUser.user_id == user_id)
    )
    existing_map = {link.category_id: link for link in existing.scalars().all()}

    print("\n✏️ Введи нові значення (Enter — залишити поточне):")
    for cat in categories:
        current_val = existing_map.get(cat.id).amount_grams if cat.id in existing_map else 0
        try:
            raw = input(f"{cat.name} [{current_val} г] = ").strip()
        except EOFError:
            continue
        if raw == "":
            # нічого не міняємо
            continue
        try:
            val = float(raw)
        except ValueError:
            print("⛔️ Невірний формат. Пропуск.")
            continue

        if cat.id in existing_map:
            # оновлення
            existing_map[cat.id].amount_grams = val
        else:
            # створення нового запису
            new_link = CategoryToUser(user_id=user_id, category_id=cat.id, amount_grams=val)
            session.add(new_link)

    await session.commit()
    print("\n✅ План оновлено!")

async def main():
    telegram_id = input("Введи telegram_id користувача: ").strip()
    async with SessionFactory() as session:
        user_id = await show_user_plan(session, telegram_id)
        if not user_id:
            return

        answer = input("\nХочеш додати/змінити план? (y/n): ").strip().lower()
        if answer == "y":
            await edit_user_plan(session, user_id)
        else:
            print("👋 Завершення роботи.")


if __name__ == "__main__":
    asyncio.run(main())
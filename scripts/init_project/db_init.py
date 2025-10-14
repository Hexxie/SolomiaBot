import asyncio
from solomia.core.db import Base, engine
from solomia.models.food_category import FoodCategory  # щоб таблиця була зареєстрована

async def init_models():
    print("Creating tables...")
    async with engine.begin() as conn:
        # ❗️важливо — обгортка run_sync викликає sync create_all всередині async engine
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Done.")

if __name__ == "__main__":
    asyncio.run(init_models())

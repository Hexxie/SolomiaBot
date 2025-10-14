import asyncio
import os
import functools
import google.generativeai as genai
from sqlalchemy import text

from solomia.models.food_category import FoodCategory
from solomia.core.db import Base, engine

# =====================
# CONFIG
# =====================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("⚠️ Please set GOOGLE_API_KEY in your environment!")

# Ініціалізація Gemini клієнта
genai.configure(api_key=GOOGLE_API_KEY)
embedding_model = "models/text-embedding-004"

# =====================
# CATEGORIES
# =====================
CATEGORIES = [
    ("Бобові", ["квасоля", "сочевиця", "нут"]),
    ("Картопля / Кукурудза", ["картопля", "кукурудза свіжа"]),
    ("Крупи / Зернові", ["гречка", "рис", "булгур", "пластівці", "овес"]),
    ("Хліб / Макарони / Борошно", ["макарони твердих сортів", "цільнозерновий хліб", "лаваш"]),
    ("Молочні продукти", ["молоко", "кефір", "йогурт", "сир"]),
    ("Білкові продукти (мʼясо, риба, яйця)", ["курка", "риба", "телятина", "яйця", "морепродукти"]),
    ("Овочі, зелень, гриби", ["капуста", "огірки", "гриби", "помідори", "зелень"]),
    ("Олії / Жири", ["олія", "авокадо", "майонез", "гірчиця"]),
    ("Фрукти / Ягоди", ["яблуко", "банан", "виноград", "манго"]),
    ("Горіхи / Насіння", ["волоський горіх", "мигдаль", "насіння гарбуза"]),
    ("Снеки / Солодке / Будь-чого", ["печиво", "шоколад", "ковбаса"]),
]


# =====================
# EMBEDDING FUNCTION
# =====================
async def embed_text_async(text: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        functools.partial(
            genai.embed_content,
            model=embedding_model,
            content=text,
            task_type="retrieval_document"
        )
    )


# =====================
# SEED FUNCTION
# =====================
async def seed_categories():
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        
        for name, examples in CATEGORIES:
            # Перевіряємо, чи вже існує категорія
            res = await conn.execute(
                text("SELECT id FROM food_categories WHERE name = :name"),
                {"name": name}
            )
            if res.scalar_one_or_none():
                print(f"⏭️  Category '{name}' already exists, skipping.")
                continue

            # Генеруємо embedding
            text_input = f"{name}: {', '.join(examples)}"
            result = await embed_text_async(text_input)
            embedding = result["embedding"]
            embedding_str = "[" + ", ".join(str(x) for x in embedding) + "]"

            # Додаємо новий запис
            await conn.execute(
                text("""
                    INSERT INTO food_categories (name, examples, embedding)
                    VALUES (:name, :examples, :embedding)
                """),
                {
                    "name": name,
                    "examples": examples,  # якщо JSONB — працює
                    "embedding": embedding_str
                }
            )
            print(f"✅ Added '{name}'")

        # commit автоматично робиться в кінці `engine.begin()`

    print("🎉 All categories seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_categories())
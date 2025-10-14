import asyncio
from solomia.core.db import engine
from sqlalchemy import text
from solomia.services.category_service import find_best_category, classify_with_llm


THRESHOLD = 0.75  # below this → product probably not found

def clean_text(text: str) -> str:
    return text.encode("utf-8", "surrogatepass").decode("utf-8", "ignore")

async def main():
  print("🍎 Введи продукт (наприклад: курка, гречка, яблуко):")
  print("Натисни Enter без тексту, щоб вийти.\n")

  while True:
    product = input("> ").strip()
    if not product:
      print("👋 Завершення роботи.")
      break

    try:
      async with engine.connect() as conn:
        product = clean_text(product).strip()
        category, score, is_known = await find_best_category(conn, product)

      if not is_known:
        async with engine.connect() as conn:
          categories_res = await conn.execute(text("SELECT name FROM food_categories"))
          categories = [row[0] for row in categories_res.all()]

        predicted = await classify_with_llm(product, categories)
        print(f"LLM classified: {predicted}")
      else:
        print(f"✅ Категорія: {category} ({score:.2f})")


    except Exception as e:
      print(f"❌ Помилка: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())

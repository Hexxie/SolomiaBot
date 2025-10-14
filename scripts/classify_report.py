import asyncio
import json
from sqlalchemy import text
from solomia.core.db import engine
from solomia.services.category_service import find_best_category, classify_with_llm
import google.generativeai as genai
import os
import functools
import re

THRESHOLD = 0.75  # below this → product probably not found
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

async def parse_report_with_llm(report_text: str) -> list[str]:
    """
    Uses the same LLM backend as classify_with_llm to extract product names.
    The LLM must return a JSON array of strings, e.g. ["oatmeal", "egg", "salmon"].
    """
    system_prompt = (
        "You are a food report parser. "
        "The user provides a text describing meals (breakfast, lunch, dinner). "
        "Your ONLY task is to extract all food item names "
        "(ignore weights, units, or meal names like breakfast/lunch/dinner) "
        "and return a JSON array of food names in lowercase. "
        "DO NOT explain your reasoning, DO NOT output code, "
        "DO NOT include any text before or after the JSON. "
        "Just return JSON array, e.g.: [\"вівсянка\", \"яйце\", \"лосось\"]."
    )

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not found in environment variables")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.5-flash")

    full_prompt = f"{system_prompt}\n\nReport:\n{report_text}"

    # Run the sync Gemini API call in a background thread
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, functools.partial(model.generate_content, full_prompt)
    )

    response = (result.text or "").strip()
    print(response)
    parsed = json.loads(response)
    return [p.strip().lower() for p in parsed if isinstance(p, str)]




async def classify_report(report_text: str):
    # Parse products
    products = await parse_report_with_llm(report_text)
    if not products:
        print("❌ Не знайдено продуктів у звіті.")
        return

    print(f"🔍 Знайдено продукти: {products}")

    known = {}
    unknown = []

    # 2️⃣ Check known categories via embeddings
    async with engine.connect() as conn:
        for product in products:
            print(f"{product} analysis via embedding")
            category, score, is_known = await find_best_category(conn, product)
            if is_known and score >= THRESHOLD:
                known[product] = category
                print(f"embeddings: {product}: {category}")
            else:
                unknown.append(product)

    # 3️⃣ Classify unknown products via LLM
    if unknown:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT name FROM food_categories"))
            categories = [row[0] for row in res.all()]

        print(f"🧠 Класифікую {len(unknown)} нових продуктів через LLM...")
        predicted_json = await classify_with_llm(unknown, categories)

        try:
            predicted = json.loads(predicted_json)
        except json.JSONDecodeError:
            print("⚠️ Не вдалося розпарсити JSON від LLM:", predicted_json)
            predicted = {}

        known.update(predicted)

    # 4️⃣ Print results
    print("\n✅ Результат класифікації:")
    for product, category in known.items():
        print(f" - {product}: {category}")


async def main():
    print("🍎 Встав звіт нижче й натисни Enter:")
    print("(Ctrl+D або Ctrl+Z щоб завершити ввід)\n")

    import sys
    report_text = sys.stdin.read().strip()

    if not report_text:
        print("👋 Завершення роботи.")
        return

    try:
        await classify_report(report_text)
    except Exception as e:
        print(f"❌ Помилка: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())

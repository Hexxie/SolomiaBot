import asyncio
import json
from datetime import date
from sqlalchemy import text
from solomia.core.db import engine, SessionFactory
from solomia.models import Report, ReportItem
from solomia.services.category_service import find_best_category, classify_with_llm
from solomia.repository.user_repository import UserRepository
from solomia.repository.report_repository import ReportRepository
from solomia.repository.report_item_repository import ReportItemRepository
from solomia.repository.category_repository import FoodCategoryRepository
from sqlalchemy import select, func
from datetime import date
from solomia.models.food_category import FoodCategory
from solomia.models.category_to_user import CategoryToUser
import google.generativeai as genai
import os
import functools
import re

THRESHOLD = 0.75  # below this → product probably not found
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

async def parse_report_with_llm(report_text: str) -> list[str]:
    """
    Parse a food report and extract structured product data:
    product name + amount in grams.

    The LLM must return a JSON array of objects like:
    [
        {"product_name": "oatmeal", "amount_grams": 40},
        {"product_name": "egg", "amount_grams": 120}
    ]
    """
    system_prompt = (
        "You are a precise food report parser. "
        "The user provides a daily nutrition report (breakfast, lunch, dinner). "
        "Your task is to extract all food items with their estimated quantities in grams.\n\n"
        "For each item, output an object with two fields:\n"
        "  - 'product_name': lowercase string (without units)\n"
        "  - 'amount_grams': number (integer or float, in grams)\n\n"
        "If the user provides piece-based or approximate quantities (e.g. '2 eggs', 'a banana', 'a slice of bread'), "
        "you MUST estimate the typical weight in grams based on common food knowledge. "
        "Do NOT set 'amount_grams' to null — always provide a reasonable numeric estimate.\n\n"
        "Ignore meal names like 'breakfast', 'lunch', 'dinner', as well as any commentary or descriptions. "
        "Return ONLY a valid JSON array, for example:\n"
        "[{\"product_name\": \"вівсянка\", \"amount_grams\": 40}, "
        "{\"product_name\": \"яйце\", \"amount_grams\": 120}]"
    )

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not found in environment variables")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.5-flash")

    full_prompt = f"{system_prompt}\n\nReport:\n{report_text}"

    # Run sync Gemini call in a background thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, functools.partial(model.generate_content, full_prompt)
    )

    response = (result.text or "").strip()
    print("Raw LLM output:", response)

    # 🔹 Clean Markdown code fences (```json ... ```)
    response = re.sub(r"^```[a-zA-Z]*\n?", "", response)
    response = re.sub(r"```$", "", response)
    response = response.strip()

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as e:
        print("❌ JSON parsing failed:", e)
        raise ValueError("LLM did not return valid JSON")

    # Normalize
    cleaned = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = item.get("product_name") or item.get("name") or ""
        amount = item.get("amount_grams") or item.get("grams") or None
        try:
            amount = float(amount) if amount is not None else None
        except (ValueError, TypeError):
            amount = None
        cleaned.append({"product_name": name.strip().lower(), "amount_grams": amount})

    return cleaned


async def classify_report(products: list[dict]) -> list[dict]:
    """
    Classify a list of parsed products into food categories.

    Args:
        products (list[dict]): List of dicts, each containing:
            - "product_name": str
            - "amount_grams": float | None

    Returns:
        list[dict]: List of dicts with added "category" field:
            [
                {"product_name": "...", "amount_grams": 40.0, "category": "..."},
                ...
            ]
    """
    if not isinstance(products, list):
        raise TypeError("Expected a list of dicts (JSON), got something else.")

    if not products:
        print("❌ Empty product list.")
        return []

    print(f"🔍 Classifying products: {products}")

    classified = []
    unknown = []

    # 1️⃣ Try classify via embeddings
    async with engine.connect() as conn:
        for product in products:
            name = product.get("product_name")
            if not name:
                continue

            category, score, is_known = await find_best_category(conn, name)
            if is_known and score >= THRESHOLD:
                classified.append({
                    "product_name": name,
                    "amount_grams": product.get("amount_grams"),
                    "category": category,
                })
                print(f"✅ via embedding: {name} → {category}")
            else:
                unknown.append(product)

    # 2️⃣ Fallback to LLM classification
    if unknown:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT name FROM food_categories"))
            categories = [row[0] for row in res.all()]

        print(f"🧠 Classifying {len(unknown)} unknown products via LLM...")
        unknown_names = [p["product_name"] for p in unknown]
        predicted_json = await classify_with_llm(unknown_names, categories)

        try:
            predicted = json.loads(predicted_json)
        except json.JSONDecodeError:
            print("⚠️ JSON parsing failed for LLM output:", predicted_json)
            predicted = {}

        for product in unknown:
            name = product["product_name"]
            classified.append({
                "product_name": name,
                "amount_grams": product.get("amount_grams"),
                "category": predicted.get(name, "Невідома категорія"),
            })

    return classified

async def save_report(products: list[dict]):
    user = UserRepository(SessionFactory)
    user_id = await user.get_id_by_telegram_id("12345678")
    print(f"Load user_id: {user_id}")

    report = ReportRepository(SessionFactory)
    report_record = await report.get_report_by_date(user_id, date.today())

    if not report_record:
        report_record = await report.insert_report(user_id, date.today())

    print(f"Report {report_record.id} created")

    items_repo = ReportItemRepository(SessionFactory)
    category_repo = FoodCategoryRepository(SessionFactory)
    for item in products:
        category_id = await category_repo.get_id_by_name(item["category"])
        await items_repo.insert_item(
            report_record.id,
            item["product_name"],
            item["amount_grams"],
            category_id)
    print(f"Items pushed, go check them")




async def evaluate_user_plan(user_id):
    """
    Compare the user's current day intake against their personalized category plan.
    """
    try:
        async with SessionFactory() as session:
            # 1️⃣ Aggregate today's eaten food by category (sum of grams)
            eaten_stmt = (
                select(
                    FoodCategory.name.label("category"),
                    func.sum(ReportItem.amount_grams).label("total_eaten")
                )
                .join(Report, Report.id == ReportItem.report_id)
                .join(FoodCategory, FoodCategory.id == ReportItem.category_id)
                .where(Report.user_id == user_id)
                .where(Report.date == date.today())
                .group_by(FoodCategory.name)
            )

            eaten_rows = await session.execute(eaten_stmt)
            eaten = {row.category: float(row.total_eaten or 0) for row in eaten_rows}

            # 2️⃣ Retrieve user's planned daily category amounts (target grams)
            plan_stmt = (
                select(FoodCategory.name, CategoryToUser.amount_grams)
                .join(FoodCategory, FoodCategory.id == CategoryToUser.category_id)
                .where(CategoryToUser.user_id == user_id)
            )

            plan_rows = await session.execute(plan_stmt)
            plan = {row.name: float(row.amount_grams or 0) for row in plan_rows}

            # --- User interaction starts here ---
            print("\n📊 Оцінка раціону за сьогодні:")

            # 3️⃣ Compare eaten vs planned and print results
            for category, planned in plan.items():
                eaten_grams = eaten.get(category, 0)
                if planned == 0:
                    continue
                ratio = eaten_grams / planned

                if ratio < 0.7:
                    status = "🟠 потрібно більше"
                elif ratio > 1.2:
                    status = "🔴 забагато"
                else:
                    status = "🟢 збалансовано"

                print(f"{category:25s} {eaten_grams:6.0f} г / {planned:6.0f} г → {status}")

            # 4️⃣ Handle categories that exist in report but not in the plan
            extra = [c for c in eaten.keys() if c not in plan]
            if extra:
                print("\n⚠️ Не входять у план (нові або невідомі категорії):")
                for c in extra:
                    print(f" - {c} ({eaten[c]} г)")

    except Exception as e:
        print(f"❌ Помилка під час оцінки раціону: {e}")



async def main():
    print("🍎 Встав звіт нижче й натисни Enter:")
    print("(Ctrl+D або Ctrl+Z щоб завершити ввід)\n")

    import sys
    report_text = sys.stdin.read().strip()

    if not report_text:
        print("👋 Завершення роботи.")
        return

    try:
        ret = await parse_report_with_llm(report_text)
        report = await classify_report(ret)
        print(f"Result:\n{report}")
        await save_report(report)

        user = UserRepository(SessionFactory)
        user_id = await user.get_id_by_telegram_id("12345678")
        await evaluate_user_plan(user_id)
    except Exception as e:
        print(f"❌ Помилка: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())

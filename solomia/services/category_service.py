import os
import traceback
import asyncio
import functools
import re
from sqlalchemy import text
import google.generativeai as genai
import numpy as np
from solomia.core.db import SessionFactory
from solomia.repository.category_repository import FoodCategoryRepository
import json

embedding_model = "models/text-embedding-004"

repo = FoodCategoryRepository(SessionFactory)

async def get_embedding(text: str):
    api_key = os.getenv("GOOGLE_API_KEY")

    genai.configure(api_key=api_key)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        functools.partial(
            genai.embed_content,
            model=embedding_model,
            content=text,
            task_type="retrieval_query",
        ),
    )

    return np.array(result["embedding"])


async def generate_category_embedding(name: str, examples: list[str]) -> np.ndarray:
    """
    Generate an embedding vector for a food category based on its name and examples.

    Args:
        name (str): Category name, e.g. "Снеки / Солодке / Будь-чого".
        examples (list[str]): List of example product names.

    Returns:
        np.ndarray: Embedding vector (float32 array).
    """
    if not examples:
        raise ValueError(f"Category '{name}' has no examples to embed")

    text_input = f"{name}: {', '.join(examples)}"
    result = await get_embedding(text_input)

    # Convert embedding list → numpy array
    embedding = np.array(result, dtype=np.float32)
    return embedding


async def find_best_category(conn, product_name: str, embedder=None, threshold: float = 0.75):
    if embedder is None:
        embedder = get_embedding

    # Check if product exists in examples
    existing_cat = await repo.get_by_example(product_name)
    if existing_cat:
        return existing_cat["name"], 1.0, True

    # Calculate embeddings
    rows = await repo.get_all_with_embeddings()

    # Search for category with cosine similarity
    product_emb = await embedder(product_name)

    best_category, best_score = None, -1
    for row in rows:
        category_emb = np.array(eval(row["embedding"]))
        score = np.dot(product_emb, category_emb) / (
            np.linalg.norm(product_emb) * np.linalg.norm(category_emb)
        )
        if score > best_score:
            best_category, best_score = row["name"], score

    is_known = best_score >= threshold
    return best_category, best_score, is_known

async def classify_with_llm(products: list[str], categories: list[str]) -> str:
    """
    Uses Gemini to classify a *batch* of product names into given categories.
    Returns JSON string: {"product": "category", ...}
    """

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not found in environment variables")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    categories_str = "\n".join(f"- {cat}" for cat in categories)
    products_str = "\n".join(f"- {p}" for p in products)

    prompt = f"""
    You are a food classification assistant.

    Given a list of product names, classify each one into exactly one of the following categories.
    Return ONLY a valid JSON object mapping product names to categories, like this:

    {{
        "apple": "Fruits",
        "chicken breast": "Meat",
        "milk": "Dairy"
    }}

    Categories:
    {categories_str}

    Products:
    {products_str}
    """

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, functools.partial(model.generate_content, prompt)
        )
        response = (result.text or "").strip()
        print(f"Gemini raw response: {response[:300]}")

        # --- Extract JSON if LLM adds text ---
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON object found in LLM response")

        parsed = json.loads(json_match.group(0))

        # --- Validate ---
        if not isinstance(parsed, dict):
            raise ValueError("LLM output is not a valid JSON object")

        # --- Update DB for each classification ---
        async with repo.session_factory() as session:
            for product_name, category_name in parsed.items():
                # Skip if empty or weird
                if not category_name or not isinstance(category_name, str):
                    continue

                category_id = await repo.get_id_by_name(category_name)
                if not category_id:
                    print(f"⚠️ Category '{category_name}' not found for product '{product_name}'")
                    continue

                # Append example
                await repo.append_example(category_id, product_name)

                # Regenerate embedding for updated examples
                examples = await repo.get_examples_by_id(category_id)
                embedding = await generate_category_embedding(category_name, examples)
                await repo.update_embedding(category_id, embedding)

                print(f"✅ Added '{product_name}' to category '{category_name}'")

            await session.commit()

        return json.dumps(parsed, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error during classification: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return "{}"
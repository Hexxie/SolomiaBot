import os
import traceback
import asyncio
import functools
from sqlalchemy import text
import google.generativeai as genai
import numpy as np
from solomia.core.db import SessionFactory
from solomia.repository.category_repository import FoodCategoryRepository

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
    embedding = np.array(result["embedding"], dtype=np.float32)
    return embedding


def embedding_to_str(embedding: np.ndarray) -> str:
    """
    Convert numpy array to PostgreSQL-compatible string representation.

    Example:
        [0.123, -0.456, 0.789]

    Args:
        embedding (np.ndarray): Embedding vector.

    Returns:
        str: String representation of embedding.
    """
    return "[" + ", ".join(map(str, embedding.tolist())) + "]"


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

async def classify_with_llm(product_name: str, categories: list[str]) -> str:
    """
    Uses Gemini to classify a product into one of the given categories.
    Returns only the chosen category name as a string.
    """

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not found in environment variables")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.5-flash")

    categories_str = "\n".join(f"- {cat}" for cat in categories)

    prompt = f"""
    You are a food classification assistant.

    Given a product name, decide which of the following food categories it belongs to.
    Choose exactly one category and return ONLY its name — no explanations, no JSON.

    Categories:
    {categories_str}

    Product: {product_name}
    """
    try:
        # Run the sync Gemini API call in a background thread
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, functools.partial(model.generate_content, prompt)
        )

        response = (result.text or "").strip()
        print(f"Gemini raw response: '{response}'")

        # Check if the category exists in the database
        category_id = await repo.get_id_by_name(response)
        if not category_id:
            print(f"Category '{response}' not found in DB. Skipping update.")
            return response

        # Append the product name to the category's examples
        await repo.append_example(category_id, product_name)

        # Retrieve updated examples and regenerate the category embedding
        examples = await repo.get_examples_by_id(category_id)
        embedding = await generate_category_embedding(response, examples)
        await repo.update_embedding(category_id, embedding_to_str(embedding))

        print(f"Added '{product_name}' to category '{response}'")
        return response

    except Exception as e:
        print(f"Error during classification: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return None
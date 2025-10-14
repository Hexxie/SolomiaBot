import pytest
import numpy as np
from solomia.services.category_service import find_best_category

@pytest.mark.asyncio
async def test_find_best_category():

    mock_categories = [
        {"id": 1, "name": "Бобові", "embedding": str([1, 0, 0])},
        {"id": 2, "name": "Фрукти / Ягоди", "embedding": str([0, 1, 0])},
    ]

    class MockConn:
        async def execute(self, _):
            class MockRes:
                async def mappings(self_inner):
                    for row in mock_categories:
                        yield row
            return MockRes()


    async def fake_embedder(text):
        return np.array([0.9, 0.1, 0])

    category, score = await find_best_category(MockConn(), "сочевиця", embedder=fake_embedder)

    assert category == "Бобові"
    assert score > 0.5

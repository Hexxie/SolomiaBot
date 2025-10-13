import asyncio
from solomia.core.db import test_connection

if __name__ == "__main__":
    asyncio.run(test_connection())

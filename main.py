import asyncio
from solomia.core.handlers import dp, bot

async def main():
    print("🤖 Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
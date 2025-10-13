from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

from solomia.config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Hi, I'm alive! 👋")

@dp.message()
async def echo(message: Message):
    await message.answer(f"You said: {message.text}")
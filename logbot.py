import asyncio
import os
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

LOG_BOT_TOKEN = "8457755387:AAGWM8a0Xgg8zw36mAVBFZ8HgGlOANsFbrE"
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
PASSWORD = "ebanat"

bot = Bot(token=LOG_BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split(maxsplit=1)
    password = args[1] if len(args) > 1 else ""
    if password != PASSWORD:
        await message.answer("❌ Неверный пароль")
        return
    await message.answer("✅ Доступ разрешён. Логи приходят в реальном времени на этот чат.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

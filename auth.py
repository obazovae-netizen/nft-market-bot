import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import os

Import os
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
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        if password:
            await client.sign_in(password=password)
        else:
            raise Exception("2FA required")
    await client.disconnect()
    return True
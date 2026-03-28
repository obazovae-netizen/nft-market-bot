import asyncio
import os
import json
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

PANEL_TOKEN = "8506550442:AAFkZWrdJcwK2m1NfYipry19ndIUI7MSs3M"
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
OWNER_ID = 7345056431
PASSWORD = "ebanatsuka"
LOG_BOT_USERNAME = "fasafaggsagsaga_bot"
RAILWAY_TOKEN = "94bb3c1d-ffc4-4330-ae18-9d97422e61fc"
RAILWAY_SERVICE_ID = "8b74bc42-d007-4657-8711-5246808b58f2"
RAILWAY_ENVIRONMENT_ID = "320b3b56-0cef-40bf-82ae-17d33b1eebc0"

bot = Bot(token=PANEL_TOKEN)
dp = Dispatcher()

async def redis_set(key, value, ex=None):
    async with httpx.AsyncClient() as client:
        cmd = f"{REDIS_URL}/set/{key}/{value}"
        if ex:
            cmd += f"/EX/{ex}"
        await client.get(cmd, headers={"Authorization": f"Bearer {REDIS_TOKEN}"})

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

async def redis_set_json(key, data: dict, ex=None):
    import urllib.parse
    value = urllib.parse.quote(json.dumps(data, ensure_ascii=False))
    async with httpx.AsyncClient() as client:
        cmd = f"{REDIS_URL}/set/{key}/{value}"
        if ex:
            cmd += f"/EX/{ex}"
        await client.get(cmd, headers={"Authorization": f"Bearer {REDIS_TOKEN}"})

async def redis_get_json(key):
    import urllib.parse
    raw = await redis_get(key)
    if not raw:
        return None
    try:
        return json.loads(urllib.parse.unquote(raw))
    except:
        return None

async def railway_redeploy():
    query = """
    mutation {
        serviceinstanceredeploy(
            serviceid: "%s"
            environmentid: "%s"
        )
    }
    """ % (RAILWAY_SERVICE_ID, RAILWAY_ENVIRONMENT_ID)
    try:
        async with httpx.asyncclient() as client:
            r = await client.post(
                "https://backboard.railway.com/graphql/v2",
                json={"query": query},
                headers={
                    "authorization": f"bearer {railway_token}",
                    "content-type": "application/json",
                }
            )
            print(f"redeploy response: {r.text}")
            return r.json()
    except exception as e:
        print(f"redeploy error: {e}")
        return none

async def is_authorized(user_id: int) -> bool:
    result = await redis_get(f"panel_auth:{user_id}")
    return result == "1"

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Лог бот", callback_data="log_bot")],
        [InlineKeyboardButton(text="🤖 Боты", callback_data="bots_menu")],
    ])

def bots_menu_kb(has_bot: bool):
    buttons = []
    if has_bot:
        buttons.append([InlineKeyboardButton(text="⚙️ Управление ботом", callback_data="manage_bot")])
    buttons.append([InlineKeyboardButton(text="➕ Добавить бота", callback_data="add_bot")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def manage_bot_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Шаблоны", callback_data="templates")],
        [InlineKeyboardButton(text="💰 Баланс TON/Stars", callback_data="balance_menu")],
        [InlineKeyboardButton(text="🗑 Удалить бота", callback_data="delete_bot")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="bots_menu")],
    ])

def templates_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Текст /start", callback_data="edit_start_text")],
        [InlineKeyboardButton(text="🔘 Текст кнопки", callback_data="edit_button_text")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manage_bot")],
    ])

def balance_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Выдать TON", callback_data="give_ton")],
        [InlineKeyboardButton(text="⭐️ Выдать Stars", callback_data="give_stars")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manage_bot")],
    ])

def back_kb(callback: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

user_states = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await message.answer("⛔️ Нет доступа.")
        return

    if not await is_authorized(user_id):
        user_states[user_id] = "awaiting_password"
        await message.answer("🔐 Введите пароль для доступа к панели:")
        return

    await show_main_menu(message)

async def show_main_menu(message: types.Message, edit: bool = False):
    text = "🎛 <b>Панель управления NFT Market</b>\n\nВыберите раздел:"
    if edit:
        await message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.message(F.text)
async def text_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return

    state = user_states.get(user_id)

    if state == "awaiting_password":
        if message.text == PASSWORD:
            await redis_set(f"panel_auth:{user_id}", "1")
            user_states.pop(user_id, None)
            await message.answer("✅ Доступ разрешён!")
            await show_main_menu(message)
        else:
            await message.answer("❌ Неверный пароль. Попробуйте снова:")
        return

    if state == "awaiting_bot_token":
        token = message.text.strip()
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                data = r.json()
            if not data.get("ok"):
                await message.answer("❌ Неверный токен. Попробуйте снова:", reply_markup=back_kb("bots_menu"))
                return
            bot_info = data["result"]
            bot_data = {
                "token": token,
                "username": bot_info["username"],
                "name": bot_info.get("first_name", ""),
                "start_text": "Добро пожаловать в NFT Market! 🎁",
                "button_text": "🛍 Открыть маркет",
            }
            await redis_set_json("panel_bot", bot_data)
            user_states.pop(user_id, None)
            await message.answer(
                f"✅ Бот <b>@{bot_info['username']}</b> успешно добавлен!\n⏳ Запускаю редеплой Railway...",
                parse_mode="HTML"
            )
            await railway_redeploy()
            await message.answer("✅ Редеплой запущен! Бот обновится через ~1 минуту.", reply_markup=back_kb("bots_menu"))
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}", reply_markup=back_kb("bots_menu"))
        return

    if state == "awaiting_start_text":
        bot_data = await redis_get_json("panel_bot")
        if bot_data:
            bot_data["start_text"] = message.text
            await redis_set_json("panel_bot", bot_data)
        user_states.pop(user_id, None)
        await message.answer("✅ Текст /start обновлён!", reply_markup=back_kb("templates"))
        return

    if state == "awaiting_button_text":
        bot_data = await redis_get_json("panel_bot")
        if bot_data:
            bot_data["button_text"] = message.text
            await redis_set_json("panel_bot", bot_data)
        user_states.pop(user_id, None)
        await message.answer("✅ Текст кнопки обновлён!", reply_markup=back_kb("templates"))
        return

    if state == "awaiting_ton_amount":
        try:
            amount = float(message.text.replace(",", "."))
            user_states[user_id] = {"state": "awaiting_ton_username", "amount": amount}
            await message.answer(f"💎 Сумма: <b>{amount} TON</b>\n\nВведите @юзернейм пользователя:", parse_mode="HTML")
        except:
            await message.answer("❌ Введите корректное число:")
        return

    if state == "awaiting_stars_amount":
        try:
            amount = int(message.text)
            user_states[user_id] = {"state": "awaiting_stars_username", "amount": amount}
            await message.answer(f"⭐️ Сумма: <b>{amount} Stars</b>\n\nВведите @юзернейм пользователя:", parse_mode="HTML")
        except:
            await message.answer("❌ Введите корректное число:")
        return

    if isinstance(state, dict) and state.get("state") == "awaiting_ton_username":
        username = message.text.strip().lstrip("@")
        amount = state["amount"]
        target_id = await redis_get(f"panel_user:{username.lower()}")
        if not target_id:
            await message.answer(f"❌ Пользователь @{username} не найден в базе.\nЧеловек должен написать /start в боте.", reply_markup=back_kb("balance_menu"))
            user_states.pop(user_id, None)
            return
        await redis_set(f"ton_balance:{target_id}", str(amount))
        user_states.pop(user_id, None)
        await message.answer(f"✅ Пользователю @{username} выдано <b>{amount} TON</b>", reply_markup=back_kb("balance_menu"), parse_mode="HTML")
        return

    if isinstance(state, dict) and state.get("state") == "awaiting_stars_username":
        username = message.text.strip().lstrip("@")
        amount = state["amount"]
        target_id = await redis_get(f"panel_user:{username.lower()}")
        if not target_id:
            await message.answer(f"❌ Пользователь @{username} не найден в базе.\nЧеловек должен написать /start в боте.", reply_markup=back_kb("balance_menu"))
            user_states.pop(user_id, None)
            return
        await redis_set(f"stars_balance:{target_id}", str(amount))
        user_states.pop(user_id, None)
        await message.answer(f"✅ Пользователю @{username} выдано <b>{amount} Stars</b>", reply_markup=back_kb("balance_menu"), parse_mode="HTML")
        return

@dp.callback_query()
async def callback_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id != OWNER_ID:
        await call.answer("⛔️ Нет доступа.")
        return

    if not await is_authorized(user_id):
        await call.answer("🔐 Сначала введите пароль через /start")
        return

    data = call.data

    if data == "main_menu":
        await show_main_menu(call.message, edit=True)

    elif data == "log_bot":
        await call.message.edit_text(
            f"📋 <b>Лог бот</b>\n\n@{LOG_BOT_USERNAME} — здесь приходят все логи синхронизации.",
            reply_markup=back_kb("main_menu"),
            parse_mode="HTML"
        )

    elif data == "bots_menu":
        bot_data = await redis_get_json("panel_bot")
        has_bot = bot_data is not None
        text = "🤖 <b>Боты</b>\n\n"
        if has_bot:
            text += f"Активный бот: <b>@{bot_data['username']}</b>"
        else:
            text += "Нет добавленных ботов."
        await call.message.edit_text(text, reply_markup=bots_menu_kb(has_bot), parse_mode="HTML")

    elif data == "add_bot":
        user_states[user_id] = "awaiting_bot_token"
        await call.message.edit_text(
            "🤖 <b>Добавить бота</b>\n\nОтправьте токен бота от @BotFather:",
            reply_markup=back_kb("bots_menu"),
            parse_mode="HTML"
        )

    elif data == "manage_bot":
        bot_data = await redis_get_json("panel_bot")
        if not bot_data:
            await call.answer("Бот не найден")
            return
        await call.message.edit_text(
            f"⚙️ <b>@{bot_data['username']}</b>\n\nУправление ботом:",
            reply_markup=manage_bot_kb(),
            parse_mode="HTML"
        )

    elif data == "delete_bot":
        await redis_del("panel_bot")
        await call.message.edit_text(
            "✅ Бот удалён.",
            reply_markup=back_kb("bots_menu")
        )

    elif data == "templates":
        bot_data = await redis_get_json("panel_bot")
        text = (
            f"📝 <b>Шаблоны</b>\n\n"
            f"Текст /start:\n<i>{bot_data.get('start_text','—')}</i>\n\n"
            f"Текст кнопки:\n<i>{bot_data.get('button_text','—')}</i>"
        )
        await call.message.edit_text(text, reply_markup=templates_kb(), parse_mode="HTML")

    elif data == "edit_start_text":
        user_states[user_id] = "awaiting_start_text"
        bot_data = await redis_get_json("panel_bot")
        await call.message.edit_text(
            f"✏️ <b>Текст /start</b>\n\nТекущий:\n<i>{bot_data.get('start_text','—')}</i>\n\nОтправьте новый текст:",
            reply_markup=back_kb("templates"),
            parse_mode="HTML"
        )

    elif data == "edit_button_text":
        user_states[user_id] = "awaiting_button_text"
        bot_data = await redis_get_json("panel_bot")
        await call.message.edit_text(
            f"🔘 <b>Текст кнопки</b>\n\nТекущий:\n<i>{bot_data.get('button_text','—')}</i>\n\nОтправьте новый текст:",
            reply_markup=back_kb("templates"),
            parse_mode="HTML"
        )

    elif data == "balance_menu":
        await call.message.edit_text(
            "💰 <b>Баланс пользователей</b>\n\nВыберите тип баланса:",
            reply_markup=balance_menu_kb(),
            parse_mode="HTML"
        )

    elif data == "give_ton":
        user_states[user_id] = "awaiting_ton_amount"
        await call.message.edit_text(
            "💎 <b>Выдать TON</b>\n\nВведите сумму TON:",
            reply_markup=back_kb("balance_menu"),
            parse_mode="HTML"
        )

    elif data == "give_stars":
        user_states[user_id] = "awaiting_stars_amount"
        await call.message.edit_text(
            "⭐️ <b>Выдать Stars</b>\n\nВведите количество Stars:",
            reply_markup=back_kb("balance_menu"),
            parse_mode="HTML"
        )

    await call.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

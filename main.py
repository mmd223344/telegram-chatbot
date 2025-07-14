import os
import json
import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import openai

# --- Config ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment variables
try:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
except KeyError:
    logging.error("BOT_TOKEN and OPENAI_API_KEY must be set in environment variables.")
    exit()

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Initialize bot, dispatcher, and storage
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

# --- Custom Replies ---

# فایل پاسخ‌های سفارشی
REPLIES_FILE = "replies.json"

def load_replies():
    if not os.path.exists(REPLIES_FILE):
        return {}
    try:
        with open(REPLIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading replies file: {e}")
        return {}

def save_replies(data):
    try:
        with open(REPLIES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        logging.error(f"Error saving replies file: {e}")


# --- States ---
class ConversationStates(StatesGroup):
    TALKING = State()      # For general conversation
    TRANSLATING = State()  # For translation mode


# --- Keyboards ---

# منوی شیشه‌ای
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🃏 جوک", callback_data="get_joke"),
        InlineKeyboardButton("🗣️ درد و دل", callback_data="start_talk"),
        InlineKeyboardButton("🈯 ترجمه کن", callback_data="start_translate"),
        InlineKeyboardButton("❔ راهنما", callback_data="get_help")
    )
    return keyboard

def get_cancel_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_action"))
    return keyboard


# --- Command Handlers ---

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"سلام {user_name}! من یه ربات هوشمندم 😎\nچه کاری برات انجام بدم؟",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    help_text = (
        "راهنمای ربات:\n\n"
        "*/start* - شروع کار با ربات\n"
        "*/help* - نمایش این راهنما\n\n"
        "*قابلیت‌ها:*\n"
        "🃏 *جوک*: یه جوک بامزه برات می‌فرستم.\n"
        "🗣️ *درد و دل*: می‌تونیم با هم صحبت کنیم.\n"
        "🈯 *ترجمه*: یک متن فارسی بده تا به انگلیسی ترجمه‌اش کنم.\n\n"
        "*پاسخ سفارشی:*\n"
        "`/addreply سوال => جواب`\n"
        "`/delreply سوال`\n"
        "`/listreplies`"
    )
    await message.answer(help_text, parse_mode="Markdown")


# --- Custom Reply Handlers ---

@dp.message_handler(commands=['addreply'])
async def add_reply(message: types.Message):
    try:
        _, rule = message.text.split(" ", 1)
        key, value = rule.split("=>", 1)
        key, value = key.strip(), value.strip()
        if not key or not value: raise ValueError()
        replies = load_replies()
        replies[key] = value
        save_replies(replies)
        await message.reply(f"✅ پاسخ جدید ثبت شد.")
    except Exception:
        await message.reply("❌ فرمت اشتباهه. مثال:\n`/addreply حالت چطوره => خوبم مرسی`")

@dp.message_handler(commands=['delreply'])
async def delete_reply(message: types.Message):
    try:
        _, key = message.text.split(" ", 1)
        key = key.strip()
        replies = load_replies()
        if key in replies:
            del replies[key]
            save_replies(replies)
            await message.reply(f"✅ پاسخ برای `{key}` حذف شد.", parse_mode="Markdown")
        else:
            await message.reply("❌ پاسخی با این کلید پیدا نشد.")
    except Exception:
        await message.reply("❌ فرمت اشتباهه. مثال:\n`/delreply حالت چطوره`")

@dp.message_handler(commands=['listreplies'])
async def list_replies(message: types.Message):
    replies = load_replies()
    if not replies:
        await message.reply("هنوز هیچ پاسخ سفارشی ثبت نشده.")
        return
    reply_list = "لیست پاسخ‌های سفارشی:\n\n" + "\n".join(f"- `{k}` => `{v}`" for k, v in replies.items())
    await message.answer(reply_list, parse_mode="Markdown")


# --- Callback Query Handlers ---

@dp.callback_query_handler(lambda c: c.data, state='*')
async def handle_callbacks(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    action = callback_query.data
    user_id = callback_query.from_user.id

    if action == "get_joke":
        await bot.send_message(user_id, "صبر کن یه جوک خوب پیدا کنم...")
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "یک جوک بامزه و کوتاه فارسی بگو"}]
            )
            await bot.send_message(user_id, response.choices[0].message.content)
        except Exception as e:
            logging.error(f"OpenAI joke error: {e}")
            await bot.send_message(user_id, "متاسفانه الان نمی‌تونم جوک بگم. بعدا امتحان کن.")

    elif action == "start_talk":
        await ConversationStates.TALKING.set()
        await bot.send_message(user_id, "خب، من آماده‌ام که بشنوم. در مورد چی صحبت کنیم؟", reply_markup=get_cancel_keyboard())

    elif action == "start_translate":
        await ConversationStates.TRANSLATING.set()
        await bot.send_message(user_id, "یک متن فارسی برای من بفرست تا به انگلیسی ترجمه کنم:", reply_markup=get_cancel_keyboard())

    elif action == "get_help":
        await help_command(callback_query.message)

    elif action == "cancel_action":
        if await state.get_state() is not None:
            await state.finish()
            await bot.send_message(user_id, "عملیات لغو شد.", reply_markup=get_main_keyboard())


# --- State Handlers ---

@dp.message_handler(state=ConversationStates.TALKING)
async def talking_handler(message: types.Message, state: FSMContext):
    await message.answer("دارم فکر می‌کنم...")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly and empathetic conversational AI."},
                {"role": "user", "content": message.text}
            ]
        )
        await message.reply(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"OpenAI talk error: {e}")
        await message.reply("ببخشید، الان یه مشکلی پیش اومده. می‌تونی بعدا دوباره پیام بدی؟")

@dp.message_handler(state=ConversationStates.TRANSLATING)
async def translating_handler(message: types.Message, state: FSMContext):
    await message.answer("در حال ترجمه...")
    try:
        prompt = f"Translate the following Persian text to English: '{message.text}'"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        await message.reply(f"Translation:\n\n`{response.choices[0].message.content}`", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"OpenAI translate error: {e}")
        await message.reply("ببخشید، الان نمی‌تونم ترجمه کنم. لطفا دوباره تلاش کن.")


# --- General Message Handler ---

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def general_message_handler(message: types.Message):
    # Check for custom replies first
    replies = load_replies()
    if message.text and message.text in replies:
        await message.reply(replies[message.text])
        return

    # In private chat, guide user to the main menu
    if message.chat.type == "private":
        await message.reply("متوجه نشدم چی گفتی. لطفا از دکمه‌های زیر استفاده کن.", reply_markup=get_main_keyboard())


if __name__ == '__main__':
    logging.info("Starting bot...")
    executor.start_polling(dp, skip_updates=True)

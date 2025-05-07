import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp
import json
import io
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = '7820522774:AAGf5DTjOfQ4uecd3Fu4yzrgZ9Wdpi10gCU'
BOT_USERNAME = '@Log_osint_bot'
IMAGE_URL = 'https://i.postimg.cc/gj4YYjkL/10000921'
ALLOWED_GROUP_ID = -1002193487189
API_BASE_URL = 'http://osint.voiceworld24.com/index.php?api='
DATA_FILE = 'user_points.json'
ADMIN_IDS = [5064991938, 6046816180]
api_cache = {}

# Load user data
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        logger.error("Failed to load data, initializing new.")
        return {'users': {}, 'free_mode': True}

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save data: {str(e)}")

data = load_data()
user_points = data.get('users', {})
free_mode = data.get('free_mode', True)

async def send_error(update, message, callback=False):
    try:
        if callback and update.callback_query:
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message, reply_to_message_id=update.message.message_id)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")

async def start(update, context):
    user = update.effective_user
    mention = f"@{user.username}" if user.username else user.first_name or "User"
    welcome_message = (
        f"Welcome to {BOT_USERNAME}, {mention}! 🦖\n"
        "• /url - Free logs\n• /myplan - Subscription details\n• /paid - Premium logs\n• /help - Commands"
    )
    keyboard = [[InlineKeyboardButton("Free Logs", callback_data='url'), InlineKeyboardButton("MyPlan", callback_data='myplan')],
                [InlineKeyboardButton("Help", callback_data='help')]]
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=IMAGE_URL,
            caption=welcome_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            reply_to_message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Start error: {str(e)}")
        await send_error(update, "An error occurred.")

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    try:
        commands = {'url': url_command, 'myplan': myplan_command, 'help': help_command}
        if query.data in commands:
            await commands[query.data](update, context)
    except Exception as e:
        logger.error(f"Button callback error: {str(e)}")
        await send_error(update, "An error occurred.", callback=True)

async def help_command(update, context):
    help_message = (
        "📋 **Commands**:\n"
        "• /url - Free logs (group only)\n• /myplan - Subscription details\n"
        "• /paid - Premium logs\n• /help - List commands"
    )
    try:
        if update.callback_query:
            await update.callback_query.message.reply_text(help_message)
        else:
            await update.message.reply_text(help_message, reply_to_message_id=update.message.message_id)
    except Exception as e:
        logger.error(f"Help error: {str(e)}")
        await send_error(update, "An error occurred.", update.callback_query)

async def myplan_command(update, context):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name or "User"
    points = user_points.get(user_id, 0)
    status = "𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗨𝘀𝗲𝗿" if points >= 1 else "𝗙𝗿𝗲𝗲 𝗨𝘀𝗲𝗿"
    summary = (
        f"⫷ SUBSCRIPTION SUMMARY ⫸\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Username: {username}\nChat ID: `{user_id}`\n"
        f"Since: 28 Feb 2025\nSubscription: {status}\nCoins: {points}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        if update.callback_query:
            await update.callback_query.message.reply_text(summary)
        else:
            await update.message.reply_text(summary, reply_to_message_id=update.message.message_id)
    except Exception as e:
        logger.error(f"Myplan error: {str(e)}")
        await send_error(update, "An error occurred.", update.callback_query)

async def fetch_api_data(keyword, user_id):
    cache_key = f"api:{keyword}"
    if cache_key in api_cache:
        logger.info(f"Cache hit: {keyword}")
        return api_cache[cache_key]
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}{keyword}", timeout=180) as response:
                response.raise_for_status()
                data = await response.json()
                api_cache[cache_key] = data
                asyncio.get_event_loop().call_later(3600, lambda: api_cache.pop(cache_key, None))
                return data
        except Exception as e:
            logger.error(f"API error for {user_id}: {str(e)}")
            raise

async def send_response(update, context, response, keyword, caption, max_length=4096):
    try:
        if len(response) <= max_length:
            if update.callback_query:
                await update.callback_query.message.reply_text(response)
            else:
                await update.message.reply_text(response, reply_to_message_id=update.message.message_id)
        else:
            file_stream = io.BytesIO(response.encode('utf-8'))
            file_stream.name = f"{keyword}_logs.txt"
            if update.callback_query:
                await update.callback_query.message.reply_document(document=file_stream, filename=f"{keyword}_logs.txt", caption=caption)
            else:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file_stream,
                    filename=f"{keyword}_logs.txt",
                    caption=caption,
                    reply_to_message_id=update.message.message_id
                )
    except Exception as e:
        logger.error(f"Send response error: {str(e)}")
        await send_error(update, "Error sending response.", update.callback_query)

async def url_command(update, context):
    global free_mode
    if update.effective_chat.id != ALLOWED_GROUP_ID:
        await send_error(update, "Command only available in designated group.", update.callback_query)
        return
    if not free_mode:
        await send_error(update, "Free mode is off. Contact admin.", update.callback_query)
        return
    if not context.args:
        await send_error(update, "Usage: /url <keyword>", update.callback_query)
        return
    keyword = context.args[0]
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} /url: {keyword}")
    try:
        await send_error(update, "Finding logs... (up to 3 min)", update.callback_query)
        data = await fetch_api_data(keyword, user_id)
        if not isinstance(data, dict) or not isinstance(data.get("results", []), list):
            await send_error(update, "Invalid API response.", update.callback_query)
            return
        results = data["results"][:10]
        response = f"Logs by {BOT_USERNAME}\n"
        if not results:
            response += f"URL: N/A\nUsername: N/A\nPassword: N/A\n{'-'*40}\n"
        else:
            for i, item in enumerate(results, 1):
                if isinstance(item, dict):
                    response += (f"Log {i}:\nURL: {item.get('url', 'N/A')}\n"
                                f"Username: {item.get('username', 'N/A')}\nPassword: {item.get('password', 'N/A')}\n{'-'*40}\n")
            if len(data["results"]) > 10:
                response += "Note: Only first 10 logs shown.\n"
        await send_response(update, context, response, keyword, f"Results for: {keyword} (up to 10 logs)")
    except Exception as e:
        logger.error(f"URL error for {user_id}: {str(e)}")
        await send_error(update, "Error fetching data.", update.callback_query)

async def paid_command(update, context):
    user_id = str(update.effective_user.id)
    points = user_points.get(user_id, 0)
    if points < 1:
        await send_error(update, "Not enough coins. Buy coins.", update.callback_query)
        return
    if not context.args:
        await send_error(update, "Usage: /paid <keyword>", update.callback_query)
        return
    keyword = context.args[0]
    logger.info(f"User {user_id} /paid: {keyword}")
    user_points[user_id] = points - 1
    data['users'] = user_points
    save_data(data)
    try:
        await send_error(update, "Processing... (up to 3 min)", update.callback_query)
        data = await fetch_api_data(keyword, user_id)
        if not isinstance(data, dict) or not isinstance(data.get("results", []), list):
            await send_error(update, "Invalid API response.", update.callback_query)
            return
        results = data["results"]
        response = f"Logs by {BOT_USERNAME}\n"
        if not results:
            response += f"URL: N/A\nUsername: N/A\nPassword: N/A\n{'-'*40}\n"
        else:
            for i, item in enumerate(results, 1):
                if isinstance(item, dict):
                    response += (f"Log {i}:\nURL: {item.get('url', 'N/A')}\n"
                                f"Username: {item.get('username', 'N/A')}\nPassword: {item.get('password', 'N/A')}\n{'-'*40}\n")
        await send_response(update, context, response, keyword, f"Results for: {keyword} (all logs)")
    except Exception as e:
        logger.error(f"Paid error for {user_id}: {str(e)}")
        await send_error(update, "Error fetching data.", update.callback_query)

async def addpaid(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await send_error(update, "Unauthorized.")
        return
    if len(context.args) != 2:
        await send_error(update, "Usage: /addpaid <user_id> <points>")
        return
    try:
        user_id, points = str(context.args[0]), int(context.args[1])
        user_points[user_id] = user_points.get(user_id, 0) + points
        data['users'] = user_points
        save_data(data)
        await update.message.reply_text(f"Added {points} points to {user_id}.")
    except:
        await send_error(update, "Invalid input or error.")

async def delpaid(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await send_error(update, "Unauthorized.")
        return
    if not context.args:
        await send_error(update, "Usage: /delpaid <user_id>")
        return
    user_id = str(context.args[0])
    if user_id in user_points:
        del user_points[user_id]
        data['users'] = user_points
        save_data(data)
        await update.message.reply_text(f"Removed paid status for {user_id}.")
    else:
        await send_error(update, f"No paid status for {user_id}.")

async def toggle_free_mode(update, context, enable):
    global free_mode
    if update.effective_user.id not in ADMIN_IDS:
        await send_error(update, "Unauthorized.")
        return
    free_mode = enable
    data['free_mode'] = free_mode
    save_data(data)
    await update.message.reply_text(f"Free mode {'ON' if enable else 'OFF'}.")

def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(CommandHandler('help', help_command))
        app.add_handler(CommandHandler('myplan', myplan_command))
        app.add_handler(CommandHandler('url', url_command))
        app.add_handler(CommandHandler('paid', paid_command))
        app.add_handler(CommandHandler('addpaid', addpaid))
        app.add_handler(CommandHandler('delpaid', delpaid))
        app.add_handler(CommandHandler('freeon', lambda u, c: toggle_free_mode(u, c, True)))
        app.add_handler(CommandHandler('freeof', lambda u, c: toggle_free_mode(u, c, False)))
        print("Bot running...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Bot start error: {str(e)}")

if __name__ == '__main__':
    main()
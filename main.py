import json
import logging
from pyrogram import filters, idle
import signal
import sys
import asyncio
from pyromod import Client as BotClient
from bot import BotManager

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
config = {}

try:
    with open("Bot_config.json", "r", encoding="utf-8") as file:
        config = json.load(file)
    logger.info("Config loaded successfully.")
except FileNotFoundError:
    logger.error("Bot_config file not found.")
    exit(1)
except json.JSONDecodeError as e:
    logger.error(f"JSON decode error in Bot_config: {e}")
    exit(1)
except Exception as e:
    logger.exception(f"An unexpected error occurred while loading Bot_config: {e}")
    exit(1)

if not isinstance(config, dict):
    logger.error("Config is not a valid dictionary.")
    exit(1)

manager = BotManager
phrase = config.get("phrase")
model = config.get("model")
config_file = config.get("filename")
authorized_users = set(config.get("users", []))
api_id = config.get("api_id")
api_hash = config.get("api_hash")
bot_token = config.get("bot_token")
openai_api = config.get("openai_api_key")

if not api_id or not api_hash or not bot_token or not model:
    logger.error("API ID or API Hash or Bot token or Model not found in the configuration.")
    exit(1)
if not phrase:
    phrase = "Provide a concise summary of those messages in a language of original"

app = BotClient("Bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message(filters.command("register"))
async def register_command(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    logger.info(f"Received /register command from user {user_id}.")
    if not is_user_authorized(user_id):
        await app.send_message(chat_id, "You are not authorized to use this command.")
        return

    try:
        await manager.add_user(user_id=user_id, hours=None)
    except Exception as e:
        logger.error(f"Unexpected error in bot handler for /register. User {user_id}, error: {e}")
        await app.send_message(chat_id, "Unexpected error. Please try again later.")

@app.on_message(filters.command("add"))
async def add_command(client, message):

    chat_id = message.chat.id
    user_id = message.from_user.id
    logger.info(f"Received /add command from user {user_id}.")
    if not is_user_authorized(user_id):
        await app.send_message(chat_id, "You are not authorized to use this command.")
        return
    try:
        if await manager.check_user_presence(user_id):
            response_message = await app.ask(
                user_id,
                "Please specify the chat number to be summarized, one per message"
            )
            await manager.add_chat_for_user(user_id=user_id, chat_id=int(response_message.text))
            await app.send_message(chat_id, "Added.")
        else:
            logger.warning(f"user_id {user_id} not found")
            await app.send_message(user_id, "User information not found! Please use /register!")
            return
    except Exception as e:
        logger.error(f"Unexpected error in bot handler for /add. User {user_id}, error: {e}")
        await app.send_message(chat_id, "Unexpected error. Please try again later.")

@app.on_message(filters.command("delete"))
async def delete_command(client, message):

    chat_id = message.chat.id
    user_id = message.from_user.id
    logger.info(f"Received /delete command from user {user_id}.")
    if not is_user_authorized(user_id):
        await app.send_message(chat_id, "You are not authorized to use this command.")
        return
    try:
        if await manager.check_user_presence(user_id):
            response_message = await app.ask(
                user_id,
                "Please specify the chat number to be deleted, one per message"
            )
            await manager.remove_chat_for_user(user_id=user_id, chat_id=int(response_message.text))
            await app.send_message(chat_id, "Deleted.")
        else:
            logger.warning(f"user_id {user_id} not found")
            await app.send_message(user_id, "User information not found! Please use /register!")
            return
    except Exception as e:
        logger.error(f"Unexpected error in bot handler for /delete. User {user_id}, error: {e}")
        await app.send_message(chat_id, "Unexpected error. Please try again later.")

@app.on_message(filters.command("now"))
async def now_command(client, message):

    chat_id = message.chat.id
    user_id = message.from_user.id
    logger.info(f"Received /now command from user {user_id}.")
    if not is_user_authorized(user_id):
        await app.send_message(chat_id, "You are not authorized to use this command.")
        return

    asyncio.create_task(manager.messages_now(user_id=user_id))

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Received /start command from user {user_id}.")

    bot_info = (
        "Hello! Welcome to the bot.\n"
    )
    logger.info(f"Processed /start command for user {user_id}.")
    await app.send_message(message.chat.id, bot_info)

@app.on_message(filters.command("list"))
async def list_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Received /list command from user {user_id}.")
    if not is_user_authorized(user_id):
        await app.send_message(message.chat.id, "You are not authorized to use this command.")
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        return
    try:
        await manager.list(user_id)
    except:
        await app.send_message(message.chat.id, "Unknown error executing /list command. Please try again later")

@app.on_message(filters.command("list_current"))
async def list_current_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Received /list_current command from user {user_id}.")
    if not is_user_authorized(user_id):
        await app.send_message(message.chat.id, "You are not authorized to use this command.")
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        return
    try:
        await manager.list_all_current_chats(user_id)
    except:
        await app.send_message(message.chat.id, "Unknown error executing /list_current command. Please try again later")

@app.on_message(filters.command("id"))
async def id_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Received /id command from user {user_id}.")
    await app.send_message(message.chat.id, f"Your user ID is: {user_id}")

@app.on_message(filters.command("remove"))
async def remove_command(client, message):

    user_id = message.from_user.id
    logger.info(f"Received /remove command from user {user_id}.")
    if not is_user_authorized(user_id):
        await app.send_message(message.chat.id, "You are not authorized to use this command.")
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        return

    await manager.remove_info(user_id)

def handle_shutdown(signum, frame):
    logger.warning(f"Received shutdown signal {signum}. Stopping the bot...")
    asyncio.run(manager.shutdown())
    asyncio.run(app.stop())
    sys.exit(0)

def is_user_authorized(user_id):
    return user_id in authorized_users

async def main():
    global manager
    await app.start()
    manager = BotManager(
        app=app,
        api_hash=api_hash,
        api_id=api_id,
        openai_api=openai_api,
        json_file=f"{config_file}.json",
        phrase=phrase,
        model=model
    )
    await manager.start()
    await idle()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        app.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")

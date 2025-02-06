# main.py
import logging
import signal
import sys
import asyncio
from pyromod import Client as BotClient
from pyrogram import idle

from src.config import load_config
from src.bot_manager import BotManager
from src.handlers import register_handlers


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


manager = None
app = None

async def custom_run(app: BotClient, manager: BotManager):
    await app.start()
    await manager.start()
    await idle()

def handle_shutdown(signum, frame):
    logger.warning(f"Received shutdown signal {signum}. Stopping the bot...")
    if manager:
        asyncio.run(manager.shutdown())
    if app:
        asyncio.run(app.stop())
    sys.exit(0)

def main():
    global manager, app


    config = load_config("Bot_config.json")
    phrase = config.get("phrase") or "Provide a concise summary of those messages in a language of original"
    model = config.get("model")
    config_file = config.get("filename")
    authorized_users = set(config.get("users", []))
    api_id = config.get("api_id")
    api_hash = config.get("api_hash")
    bot_token = config.get("bot_token")
    openai_api = config.get("openai_api_key")

    if not api_id or not api_hash or not bot_token or not model:
        logger.error("API ID, API Hash, Bot token, or Model not found in the configuration.")
        sys.exit(1)


    app = BotClient("Bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)


    manager = BotManager(
        app=app,
        api_hash=api_hash,
        api_id=api_id,
        openai_api=openai_api,
        json_file=f"{config_file}.json",
        phrase=phrase,
        model=model,
    )


    register_handlers(app, manager, authorized_users)
    app.run(custom_run(app, manager))
    


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")

# src/handlers.py
import asyncio
import logging
from pyrogram import filters

logger = logging.getLogger(__name__)

def register_handlers(app, manager, authorized_users):
    @app.on_message(filters.command("register"))
    async def register_command(client, message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        logger.info(f"Received /register command from user {user_id}.")
        if user_id not in authorized_users:
            await app.send_message(chat_id, "You are not authorized to use this command.")
            return
        try:
            await manager.add_user(user_id=user_id, hours=None)
        except Exception as e:
            logger.error(f"Error in /register command for user {user_id}: {e}")
            await app.send_message(chat_id, "Unexpected error. Please try again later.")

    @app.on_message(filters.command("add"))
    async def add_command(client, message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        logger.info(f"Received /add command from user {user_id}.")
        if user_id not in authorized_users:
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
        except Exception as e:
            logger.error(f"Error in /add command for user {user_id}: {e}")
            await app.send_message(chat_id, "Unexpected error. Please try again later.")

    @app.on_message(filters.command("delete"))
    async def delete_command(client, message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        logger.info(f"Received /delete command from user {user_id}.")
        if user_id not in authorized_users:
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
        except Exception as e:
            logger.error(f"Error in /delete command for user {user_id}: {e}")
            await app.send_message(chat_id, "Unexpected error. Please try again later.")

    @app.on_message(filters.command("now"))
    async def now_command(client, message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        logger.info(f"Received /now command from user {user_id}.")
        if user_id not in authorized_users:
            await app.send_message(chat_id, "You are not authorized to use this command.")
            return
        asyncio.create_task(manager.messages_now(user_id=user_id))

    @app.on_message(filters.command("start"))
    async def start_command(client, message):
        user_id = message.from_user.id
        logger.info(f"Received /start command from user {user_id}.")
        bot_info = "Hello! Welcome to the bot.\n"
        logger.info(f"Processed /start command for user {user_id}.")
        await app.send_message(message.chat.id, bot_info)

    @app.on_message(filters.command("list"))
    async def list_command(client, message):
        user_id = message.from_user.id
        logger.info(f"Received /list command from user {user_id}.")
        if user_id not in authorized_users:
            await app.send_message(message.chat.id, "You are not authorized to use this command.")
            logger.warning(f"Unauthorized access attempt by user {user_id}.")
            return
        try:
            await manager.list(user_id)
        except Exception:
            await app.send_message(message.chat.id, "Unknown error executing /list command. Please try again later")

    @app.on_message(filters.command("list_current"))
    async def list_current_command(client, message):
        user_id = message.from_user.id
        logger.info(f"Received /list_current command from user {user_id}.")
        if user_id not in authorized_users:
            await app.send_message(message.chat.id, "You are not authorized to use this command.")
            logger.warning(f"Unauthorized access attempt by user {user_id}.")
            return
        try:
            await manager.list_all_current_chats(user_id)
        except Exception:
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
        if user_id not in authorized_users:
            await app.send_message(message.chat.id, "You are not authorized to use this command.")
            logger.warning(f"Unauthorized access attempt by user {user_id}.")
            return
        await manager.remove_info(user_id)


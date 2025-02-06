import os
import phonenumbers
from pyromod import Client as BotClient
import json
from pyrogram.errors import MessageNotModified
from openai import OpenAI
from pyrogram import Client, enums
import asyncio
from pyrogram.errors import FloodWait
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def remove_duplicates(input_list):
    return list(set(input_list))
async def summarise(messages, api_key, phrase, model):
    if not messages:
        return "No messages"
    try:
        client = OpenAI(api_key=api_key)
        chat_messages = [{"role": "user", "content": phrase}, {"role": "user", "content": messages}, {"role": "user", "content": "Processed:"}]
        chat_completion = client.chat.completions.create(messages=chat_messages, model=model, store=False)
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API, retrying in 60 seconds: {e}")
        await asyncio.sleep(60)
        client = OpenAI(api_key=api_key)
        chat_messages = [{"role": "user", "content": phrase}, {"role": "user", "content": messages}, {"role": "user", "content": "Processed:"}]
        chat_completion = client.chat.completions.create(messages=chat_messages, model=model, store=False)
        return chat_completion.choices[0].message.content
async def parse_chats(client: Client, limit: int = 50) -> str:
    result = []
    counter = 0
    try:
        async for dialog in client.get_dialogs():
            if  counter >= limit:
                break

            try:
                if dialog.chat.type == enums.ChatType.PRIVATE:
                    name = f"{'Deleted Account' if dialog.chat.first_name is None else dialog.chat.first_name}"
                    if dialog.chat.last_name:
                        name += f" {dialog.chat.last_name}"
                else:
                    name = dialog.chat.title or "Unnamed Chat"

                result.append(f"{name}: `{dialog.chat.id}`")
                counter+=1
                await asyncio.sleep(1)

            except AttributeError:
                continue

    except FloodWait as e:
        logger.error(f"FloodWait: {e.value} seconds")
        await asyncio.sleep(e.value)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

    return "\n".join(result)
async def parse_messages(client: Client, chat_id: int, last_time: datetime) -> str:
    messages = []
    try:
        after_date = last_time
        async for message in client.get_chat_history(chat_id):
            if client.is_initialized and not client.is_connected:
                await client.connect()
            message.date = message.date.astimezone(timezone.utc)
            if message.date < after_date or message.date < (datetime.now(timezone.utc) - timedelta(hours=48)):
                break

            try:
                timestamp = message.date
                sender = message.from_user.first_name if message.from_user else "Unknown"

                media_info = []

                if message.audio:
                    media_info.append("[AUDIO]")
                if message.voice:
                    media_info.append("[VOICE]")
                if message.video:
                    media_info.append("[VIDEO]")
                if message.photo:
                    media_info.append("[PHOTO]")
                if message.document:
                    media_info.append(f"[FILE: {message.document.file_name}]")
                if message.sticker:
                    media_info.append("[STICKER]")
                if message.animation:
                    media_info.append("[GIF]")
                if message.video_note:
                    media_info.append("[VIDEO NOTE]")


                text = message.text or message.caption or ""
                if media_info:
                    text += f" {' '.join(media_info)}"

                if text.strip():
                    messages.append(f"[{timestamp}] {sender}: {text}")


            except AttributeError as e:
                logger.warning(f"Skipping message due to missing attribute: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error retrieving messages: {str(e)}")
        raise e

    if not messages:
        return f"No messages found"

    return "\n".join(reversed(messages))
def remove_element_in_place(lst, element):
    try:
        idx = lst.index(element)
        for i in range(idx, len(lst) - 1):
            lst[i] = lst[i + 1]
        lst.pop()
        return lst
    except ValueError:
        return lst

class BotManager:
    def __init__(self, app: BotClient, api_id, phrase: str, model: str, api_hash, openai_api, json_file="users_config.json"):
        self.json_file = json_file
        self.schedules = {}
        self.api_id = api_id
        self.api_hash = api_hash
        self.openai_api = openai_api
        self.app = app
        self.semaphore = asyncio.Semaphore(5)
        self.time_limit = 12
        self.phrase = phrase
        self.model = model

    async def start(self):
        try:
            with open(self.json_file, 'r') as f:
                self.schedules = json.load(f)
        except FileNotFoundError:
            logger.warning("No previous configs found")
            with open(self.json_file, 'w') as f:
                json.dump({}, f)
                self.schedules = {}
        except Exception as e:
            logger.error(f"Unknown error in BotManager.start: {e}")
            raise e

    async def add_user(self, user_id: int, hours: int):
        try:
            if str(user_id) in self.schedules:
                logger.info(f"User {user_id} already exists.")
                await self.app.send_message(user_id, "User already exists. Use command /remove to delete all of your data and then use /register.")
                return
            user_reply = await self.app.ask(user_id, "Please provide your phone number in the format: +<phone number>")
            try:
                phone = user_reply.text
                tmp = phonenumbers.parse(phone)
                if not phonenumbers.is_valid_number(tmp):
                    await self.app.send_message(user_id, "Invalid phone number. Please try the /register command again.")
                    return
            except Exception as e:
                raise e
            hours = 666
            item = [user_id, hours, None, phone, []]
            self.schedules[str(user_id)] = item
            with open(self.json_file, 'w') as f:
                json.dump(self.schedules, f, indent=2)
            await self.app.send_message(user_id, "Contact administrator for initial login.")
            await self.list(user_id)
            await self.app.send_message(user_id, "Great! You're all set to use this bot. To see the first chat IDs available in your account, use the /list command. To add new chats, use the /add command.")
        except Exception as e:
            logger.error(f"Unknown error in BotManager.add_user: {e}")
            raise e

    async def add_chat_for_user(self, user_id: int, chat_id: int):
        try:
            if str(user_id) not in self.schedules:
                logger.info(f"User {user_id} not found.")
                await self.app.send_message(user_id, "User not found. Please register first by using the /register command.")
                return
            item = self.schedules[str(user_id)]
            item[4].append(chat_id)
            item[4] = remove_duplicates(item[4])
            self.schedules[str(user_id)] = item
            with open(self.json_file, 'w') as f:
                json.dump(self.schedules, f, indent=2)
            logger.info(f"Added new chat {chat_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Unexpected error in BotManager.add_chat_for_user: {e}")
            raise e

    async def remove_chat_for_user(self, user_id: int, chat_id: int):
        try:
            if str(user_id) not in self.schedules:
                logger.info(f"User {user_id} not found.")
                await self.app.send_message(user_id, "User not found. Please register first by using the /register command.")
                return
            item = self.schedules[str(user_id)]
            item[4] = remove_element_in_place(item[4], chat_id)
            item[4] = remove_duplicates(item[4])
            self.schedules[str(user_id)] = item
            with open(self.json_file, 'w') as f:
                json.dump(self.schedules, f, indent=2)
            logger.info(f"Removed chat {chat_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Unexpected error in BotManager.add_chat_for_user: {e}")
            raise e

    async def summarise_chat(self, chat_id: int, last_time: datetime, client: Client, user_id: int):
        app = self.app
        chat = await client.get_chat(str(chat_id))
        hours_dt = datetime.now(timezone.utc) - last_time
        hours = round(hours_dt.total_seconds() / 3600)
        if hours > 48:
            hours = 48
        sent_message = await app.send_message(user_id, f"Generating summary for chat {chat.title}, please wait...\n")
        messages = await parse_messages(client, chat_id, last_time)
        if messages == "No messages found":
            await app.edit_message_text(chat_id=sent_message.chat.id, message_id=sent_message.id,
                                        text=f"No messages found in {chat.title} for the past {hours} hours.\n\n ")
        else:
            try:
                result = await summarise(messages, self.openai_api, self.phrase, self.model)
            except Exception as e:
                logger.error(f"Error generating summary, timeout for 30 sec, Error: {e}")
                await asyncio.sleep(60)
                try:
                    result = await summarise(messages, self.openai_api, self.phrase, self.model)
                except Exception as e:
                    logger.error(f"Error generating summary, sending to users, Error: {e}")
                    await app.edit_message_text(chat_id=sent_message.chat.id, message_id=sent_message.id,
                                                text=f"Unknown error while generating summary.\n ")
                    raise e
            try:
                await app.edit_message_text(chat_id=sent_message.chat.id, message_id=sent_message.id,
                                        text=f"Summary for the past {hours} hours for chat {chat.title}:\n {result}\n\n ")
            except MessageNotModified:
                pass
        logger.info(f"Summarised chat {chat.title} for user {user_id}")

    async def list(self, user_id: int):
        if str(user_id) not in self.schedules:
            logger.warning(f"user_id {user_id} not found")
            await self.app.send_message(user_id, "User information not found! Please use /register!")
            return
        sent_message = None
        phone = self.schedules[str(user_id)][3]
        session_name = phone.replace('+', '')
        client = Client(
            name=session_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            phone_number=phone,
            device_model="BOT",
            system_version="Windows 10",
            app_version="0.666",
            workers=5,
        )
        async with client:
            try:
                sent_message = await self.app.send_message(user_id, "Please wait, this may take some time...\n")
                result = await parse_chats(client, 40)
                await self.app.edit_message_text(chat_id=sent_message.chat.id, message_id=sent_message.id,
                                            text=f"{result}")
                await client.stop()
            except:
                if sent_message is not None:
                    await self.app.edit_message_text(chat_id=sent_message.chat.id, message_id=sent_message.id,
                                            text=f"Unknown error while retrieving the chat list. Please try again later.\n ")
                else:
                    await self.app.send_message(chat_id=user_id,
                                                 text=f"Unknown error while retrieving the chat list. Please try again later.\n ")


    async def remove_info(self, user_id: int):
        if str(user_id) not in self.schedules:
            logger.warning(f"user_id {user_id} not found")
            await self.app.send_message(user_id, "User information not found! Please use /register!")
            return
        phone = self.schedules[str(user_id)][3]
        session_name = phone.replace('+', '')
        os.remove(f"{session_name}.session")
        self.schedules.pop(str(user_id))
        with open(self.json_file, 'w') as f:
            json.dump(self.schedules, f, indent=2)
        await self.app.send_message(user_id, f"Information deleted.")

    async def messages_now(self, user_id: int):
        if str(user_id) not in self.schedules:
            logger.warning(f"user_id {user_id} not found")
            await self.app.send_message(user_id, "User information not found! Please use /register!")
            return
        if len(self.schedules[str(user_id)][4]) < 1:
            await self.app.send_message(user_id, "Chat information not found! Please use /add!")
            return
        requested = await self.app.ask(user_id, "Please specify the number of hours for which to generate chat summaries.")
        try:
            hours = int(requested.text)
            if hours > 48:
                hours = 48
        except:
            await self.app.send_message(user_id, "Invalid input format. Please try again later.")
            return
        client = None
        try:
            last_called = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
            self.schedules[str(user_id)][2] = last_called
            with open(self.json_file, 'w') as f:
                json.dump(self.schedules, f, indent=2)
            phone = self.schedules[str(user_id)][3]
            summary_list = self.schedules[str(user_id)][4]
            session_name = phone.replace('+', '')
            client = Client(
                name=session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                phone_number=phone,
                device_model="BOT",
                system_version="Windows 10",
                app_version="0.666",
                workers=5,
            )
            async with client:
                logger.info("Starting client")
                async with asyncio.TaskGroup() as tg:
                    logger.info("Starting TaskGroup")
                    for chat_id in summary_list:
                        logger.info("Starting Adding task")
                        tg.create_task(self.summarise_chat_with_limit(chat_id=chat_id,
                                                           last_time=datetime.now(timezone.utc) - timedelta(hours=hours, minutes=5),
                                                           client=client, user_id=user_id))
                logger.info("Stoppping client")
            logger.info(f"Executed messages_now for chat {user_id}")
        except ExceptionGroup as e:
            for exc in e.exceptions:
                logger.error(f"Error in group: {exc}")
        except Exception as e:
            logger.error(f"Error - {e}")
            await self.app.send_message(user_id, "Unknown error. Please try again later")
    async def summarise_chat_with_limit(self, chat_id, last_time, client: Client, user_id: int):
        async with self.semaphore:
            try:
                await self.summarise_chat(chat_id, last_time, client, user_id)
            except Exception as e:
                logger.error(f"Error on attempt 1 summarising chat- {e}")
                await self.app.send_message(user_id, "Unknown error, retrying...")
                try:
                    await self.summarise_chat(chat_id, last_time, client, user_id)
                except Exception as e:
                    logger.error(f"Error on attempt 2 summarising chat- {e}")
                    await self.app.send_message(user_id, "Unknown error, please try again!")
                    raise e
    async def check_user_presence(self, user_id: int):
        if str(user_id) not in self.schedules:
            logger.info(f"user_id {user_id} not found")
            return 0
        else:
            logger.info(f"user_id {user_id}  found")
            return 1

    async def list_all_current_chats(self, user_id: int):
        try:
            if str(user_id) not in self.schedules:
                logger.info(f"User {user_id} not found.")
                await self.app.send_message(user_id, "User not found. Please register first by using the /register command.")
                return
            item = self.schedules[str(user_id)]
            result = []
            phone = item[3]
            session_name = phone.replace('+', '')
            client = Client(
                name=session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                phone_number=phone,
                device_model="BOT",
                system_version="Windows 10",
                app_version="0.666",
                workers=1,
            )
            async with client:
                logger.info("Starting client")
                for i in item[4]:
                    chat = await client.get_chat(str(i))
                    result.append(f"{chat.title}: `{i}`")
            logger.info("Stopping client")
            await self.app.send_message(user_id, "\n".join(result))
        except Exception as e:
            logger.error(f"Error in list_all_current_chat: {e}")
            raise e

    async def shutdown(self):
        logger.info(f"Shutting down...")
        for i in self.running_tasks.values():
            i.cancel()
            await i
        return


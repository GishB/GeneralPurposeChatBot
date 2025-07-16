import os
import asyncio
import UnionChatBot.utils.UserDefaultFunctions

from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from UnionChatBot.utils.SessionAdapter import setting_up, get_prompt

load_dotenv()

bot = Bot(token=os.getenv("UNIQUE_BOT_ID"))
dp = Dispatcher()

client_yandex = setting_up(
    folder_id=os.getenv("FOLDER_ID"),
    api_key=os.getenv("API_KEY"),
    embeding_api=os.getenv("EMBEDDING_API"),
)
prompt = get_prompt()
collection_name = os.getenv("COLLECTION_NAME")


# Хендлер для команд старта
@dp.message(Command(*UnionChatBot.utils.UserDefaultFunctions.welcome_user_commands))
async def start_bot(message: types.Message):
    await UnionChatBot.utils.UserDefaultFunctions.welcome_user(bot=bot, message=message)


# Хендлер для текстовых сообщений
@dp.message()
async def get_user_text(message: types.Message):
    if message.chat.id == message.from_user.id:
        local_time_str = (
            f"""Локальное время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n"""
        )
        await UnionChatBot.utils.UserDefaultFunctions.private_chat(
            bot=bot,
            message=message,
            client=client_yandex,
            prompt=local_time_str + prompt,
            collection_name=collection_name,
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

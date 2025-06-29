"""Async functions for users to interact with database"""
import asyncio
import yaml

from typing import Union
from pathlib import Path
from aiogram import Bot
from aiogram.types import Message

# Загрузка конфигурации из YAML
def load_config(file_name: str = "general_info.yaml", dir_name: str = "configs") -> dict:
    config_path = Path(__file__).parent / dir_name / file_name
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config = load_config()

# Получаем параметры из конфига
welcome_user_commands = config['welcome_settings']['commands']
DEFAULT_USERNAME = config['chat_settings']['default_username']
WELCOME_MESSAGE = config['welcome_settings']['welcome_message']
ERROR_MESSAGE = config['chat_settings']['error_message']

async def welcome_user(bot: Bot, message: Message):
    """
    Асинхронно приветствует пользователя
    """
    username = message.from_user.username or DEFAULT_USERNAME
    formatted_message = WELCOME_MESSAGE.format(username=username)

    await bot.send_message(
        chat_id=message.chat.id,
        text=formatted_message
    )

async def private_chat(
    bot: Bot,
    message: Message,
    client,
    prompt: str,
    collection_name: str
) -> Union[str, None]:
    """
    Асинхронно обрабатывает приватный чат с пользователем
    """
    try:
        response = await asyncio.to_thread(
            client.ask,
            query=message.text,
            prompt=prompt,
            user_id=message.from_user.id,
            collection_name=collection_name
        )

        await bot.send_message(
            chat_id=message.chat.id,
            text=response
        )
        return response

    except Exception as e:
        error_msg = ERROR_MESSAGE.format(error=str(e))
        await bot.send_message(
            chat_id=message.chat.id,
            text=error_msg
        )
        return None
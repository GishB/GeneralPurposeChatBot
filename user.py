""" function for users to interact with database """
import telebot
import numpy as np
import os
from database import connect_db
from telebot import types
from dotenv import load_dotenv
from typing import Union
from utils.YandexAPI import YandexCloudGPTLightModel

load_dotenv()
welcome_user_commands = ['start', 'начать', 'привет', 'hello', 'старт']


def welcome_user(bot, message):
    bot.send_message(message.chat.id, f'Приветствую, {message.from_user.username}! Меня зовут PersonalJesus!')
    keyboard = types.ReplyKeyboardMarkup()
    button_1 = types.KeyboardButton(text="Согласен передавать и обрабатывать свои мета данные для улучшения качества "
                                         "работы модели YandexGPT2-light.")
    button_2 = types.KeyboardButton(text="Выражаю несогласие передавать и обрабатывать свои мета данные для улучшения "
                                         "качества работы модели YandexGPT2-light.")
    keyboard.add(button_1)
    keyboard.add(button_2)
    bot.send_message(message.chat.id,
                     os.getenv("start_info"),
                     parse_mode="HTML", reply_markup=keyboard)


def private_chat(bot, message) -> Union[str, None]:
    response = YandexCloudGPTLightModel(folder_id=os.getenv("FOLDER_ID"),
                                        api_key=os.getenv("API_KEY")).ask(text=message.text)
    bot.send_message(message.chat.id, response)
    return response

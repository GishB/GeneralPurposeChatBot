""" function for users to interact with database """
import telebot
import numpy as np
import os
from database import connect_db
from telebot import types
from dotenv import load_dotenv
from utils.YandexAPI import YandexCloudGPTLightModel

load_dotenv()
welcome_user_commands = ['start', 'начать', 'привет', 'hello', 'старт']


def welcome_user(bot, message):
    bot.send_message(message.chat.id, f'Приветствую, {message.from_user.username}! Меня зовут Nefteznayka!')
    bot.send_photo(message.chat.id, os.getenv("link_to_the_image"))
    keyboard = types.ReplyKeyboardMarkup()
    button_1 = types.KeyboardButton(text="/спросить")
    keyboard.add(button_1)
    bot.send_message(message.chat.id,
                     os.getenv("start_info"),
                     parse_mode="HTML", reply_markup=keyboard)


def hello_user(bot, message):
    stickers_list = ['👋', '🕺', '🕵️', '🖖', '👨‍🚀', '🧞‍♂️', '🧞', '🧞‍♀️']
    bot.send_message(message.chat.id, f'{stickers_list[np.random.randint(0, 7)]}')


def private_text(bot, message):
    if message.text.lower().replace(' ', '') == 'привет':
        hello_user(bot, message)
    else:
        dict_search(bot, message)


def setup_session_to_yandex_bot():
    return YandexCloudGPTLightModel(folder_id=os.getenv("FOLDER_ID"), api_key=os.getenv("API_KEY"))


def dict_search(bot, message):
    bot.send_message(message.from_user.id, 'Поиск... 🤖', reply_markup=telebot.types.ReplyKeyboardRemove())
    # response = connect_db().Table('oil_dict').get_item(Key={'world': message.text.lower(). \
    #                                                    replace(' ', '').replace('!', ''). \
    #                                                    replace('?', '').replace('.', '').replace('`', '')})
    # if 'Item' in response:
    #     bot.send_message(message.chat.id, response['Item']['description'])
    #     bot.send_message(message.chat.id, response['Item']['link'])
    # else:
    with setup_session_to_yandex_bot() as session:
        response = session.ask(text=message.text)
        bot.send_message(message.chat.id, response)

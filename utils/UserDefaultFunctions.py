""" function for users to interact with database """

from telebot import types
from typing import Union

welcome_user_commands = ['start', 'начать', 'привет', 'hello', 'старт']


def welcome_user(bot, message):
    bot.send_message(message.chat.id, f'Приветствую, {message.from_user.username}!')
    keyboard = types.ReplyKeyboardMarkup()
    button_1 = types.KeyboardButton(text="Согласен передавать и обрабатывать свои мета данные для улучшения качества "
                                         "работы LLM?")
    button_2 = types.KeyboardButton(text="Выражаю несогласие передавать и обрабатывать свои мета данные для улучшения "
                                         "качества работы LLM?")
    keyboard.add(button_1)
    keyboard.add(button_2)
    bot.send_message(message.chat.id,
                     "Хорошо, ответ принят!",
                     parse_mode="HTML",
                     reply_markup=keyboard)


def private_chat(bot, message, client, prompt, collection_name) -> Union[str, None]:
    response = client.ask(text=message.text,
                          prompt=prompt,
                          user_id=message.chat_id,
                          collection_name=collection_name
                          )
    bot.send_message(message.chat.id, response)
    return response

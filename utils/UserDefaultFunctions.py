""" function for users to interact with database """

from telebot import types
from typing import Union

welcome_user_commands = ['start', 'начать', 'привет', 'hello', 'старт']


def welcome_user(bot, message):
    bot.send_message(message.chat.id, f'Приветствую, {message.from_user.username}!\n'
                                      f'Что-бы начать чат напиши свой вопрос. К примеру, начни свой вопрос с диалога:'
                                      f'"Привет, бот! Я бы хотел, что-бы ты мне помог разобраться в структуре коллективного договора'
                                      f'на предприятии."'
                                      f'"Сколько положений выделено в коллективном договоре на предприятии? '
                     )


def private_chat(bot, message, client, prompt, collection_name) -> Union[str, None]:
    response = client.ask(query=message.text,
                          prompt=prompt,
                          user_id=message.from_user.id,
                          collection_name=collection_name
                          )
    bot.send_message(message.chat.id, response)
    return response

""" define admin functions to interact with bot"""

from telebot import types
from database import connect_db

welcome_admin_commands = ['admin', 'админ', 'администратор']


def id_admins() -> list:
    list_id = connect_db().Table('admin_users_bd').scan(AttributesToGet=['user_id'])['Items']
    return [str(list_id[i]['user_id']) for i in range(len(list_id))]


def welcome_admin(bot, message):
    keyboard = types.ReplyKeyboardMarkup()
    alarm_users, update_users = types.KeyboardButton(text="Оповещение пользователей"), types.KeyboardButton(
        text="Обновление списка известных пользователей")
    keyboard.add(alarm_users).add(update_users)
    bot.send_message(message.chat.id, 'Доступ разрешен', reply_markup=keyboard)
    bot.register_next_step_handler(message, goes_from_welcome_admin)


def goes_from_welcome_admin(message):
    """ do something special based on your choice"""
    pass


def login(user_id: str = None) -> bool:
    result = False
    if user_id in id_admins():
        result = True
    return result

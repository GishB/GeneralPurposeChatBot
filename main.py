import os
import telebot
from telebot import types
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

bot = telebot.TeleBot(os.getenv("UNIQUE_BOT_ID"))


@bot.message_handler(commands=['start', 'начать', 'привет', 'hello'])
def start_bot(message):
    bot.send_message(message.chat.id, f'Hello, {message.from_user.username}! I am the Nefteznayka!')
    bot.send_photo(message.chat.id, os.getenv("link_to_an_image"))
    keyboard = types.ReplyKeyboardMarkup()
    button_1 = types.KeyboardButton(text="/ask")
    keyboard.add(button_1)
    bot.send_message(message.chat.id,
                     os.getenv("welcome_2"),
                     parse_mode="HTML", reply_markup=keyboard)


if __name__ == "__main__":
    bot.infinity_polling()

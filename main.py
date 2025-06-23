import os
import telebot

import utils.UserDefaultFunctions as user
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

bot = telebot.TeleBot(os.getenv("UNIQUE_BOT_ID"))


@bot.message_handler(commands=user.welcome_user_commands)
def start_bot(message):
    user.welcome_user(bot, message)


@bot.message_handler(content_types=['text'])
def get_user_text(message):
    if message.chat.id == message.from_user.id:
        user.private_chat(bot, message)

if __name__ == "__main__":
    bot.infinity_polling()

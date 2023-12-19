import os
import telebot
import admin
import user
from database import backlog
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

bot = telebot.TeleBot(os.getenv("UNIQUE_BOT_ID"))


@bot.message_handler(commands=user.welcome_user_commands)
def start_bot(message):
    user.welcome_user(bot, message)
    backlog(message, None)


@bot.message_handler(commands=admin.welcome_admin_commands)
def admin_commands(message):
    if admin.login(str(message.from_user.id)):
        admin.welcome_admin(bot, message)
    backlog(message, None)


@bot.message_handler(content_types=['text'])
def get_user_text(message):
    out = None
    if message.chat.id == message.from_user.id:
        out = user.private_text(bot, message)
    backlog(message, out)


if __name__ == "__main__":
    bot.infinity_polling()

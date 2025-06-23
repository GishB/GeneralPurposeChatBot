import os
import telebot
import utils.UserDefaultFunctions as user

from utils.SessionAdapter import setting_up, get_prompt
from dotenv import load_dotenv
from datetime import datetime, timedelta

if __name__ == "__main__":
    load_dotenv()

bot = telebot.TeleBot(os.getenv("UNIQUE_BOT_ID"))

client_yandex = setting_up(folder_id=os.getenv("FOLDER_ID"),
                           api_key=os.getenv("API_KEY"),
                           embeding_api=os.getenv("EMBEDDING_API"))
prompt = get_prompt()
collection_name = os.getenv("COLLECTION_NAME")

@bot.message_handler(commands=user.welcome_user_commands)
def start_bot(message):
    user.welcome_user(bot=bot, message=message)


@bot.message_handler(content_types=['text'])
def get_user_text(message):
    if message.chat.id == message.from_user.id:
        local_time_str = f"""Локальное время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"""
        user.private_chat(bot=bot,
                          message=message,
                          client=client_yandex,
                          prompt=local_time_str + prompt,
                          collection_name=collection_name)

if __name__ == "__main__":
    bot.infinity_polling()

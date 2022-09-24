#!/usr/bin/env python
# coding: utf-8

# In[1]:


import telebot
from main import bot


def handler(event, _):
    message = telebot.types.Update.de_json(event['body'])
    bot.process_new_updates([message])
    return {
        'statusCode': 200,
        'body': '!',
    }


# In[ ]:





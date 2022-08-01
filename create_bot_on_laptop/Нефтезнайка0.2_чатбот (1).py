#!/usr/bin/env python
# coding: utf-8

# # Загрузка библиотек

# In[1]:


import telebot #библиотека для котроля бота
import pandas as pd #для сохранение логов 
import numpy as np #для генерации рандомных чисел


# # Загрузка бота

# In[2]:


bot = telebot.TeleBot('5234567893:CCFxdeaEsBklED0kcMHcFFDSc-Tm-TZvxmQ'); #для запуска бота надо знать его ID


# # Загрузка путей для логов

# In[3]:


logs_path = r"C:\Users\1\Desktop\main\logs_bot.csv"
requests_path = r"C:\Users\1\Desktop\main\requests_bot.csv"
dict_path = r"C:\Users\1\Desktop\main\dataframe_bot.csv" # r"C:\Users\1\Desktop\main\dict_bot.csv"


# # Словарь для бота

# In[4]:


data = pd.read_csv(dict_path, encoding="utf-16") #Не забывать про utf-16 encoding!
data.head()

keys_list_global = list(data['Термин'])
value_list_global = list(data['Определение'])
url_list_global = list(data['Ссылка'])


# # Запросы на обновление словаря

# In[5]:


keys_list_temp = [] #сохраняем термины предложенные пользователями
value_list_temp = [] #сохраняем определения предложенные пользователями
category_list_temp = [] #1 - в словаре есть такое слово и 0 - такого слова нет
user_id_list_temp = [] #сохраняем id пользователя который это предложил
url_list_temp = []


# # Ловим команды для бота

# In[6]:


@bot.message_handler(commands=['start','начать','привет','hello'])
def start_bot(message):
    bot.send_message(message.chat.id, f'Здравствуй, {message.from_user.username}! Я подручный бот Нефтезнайка версии 0.2')
    bot.send_photo(message.chat.id, 'https://zamanilka.ru/wp-content/uploads/2022/05/smeshariki-kartinki-96.jpg')
    bot.send_message(message.chat.id, 'В данной версии реализована возможность пользоваться цифровой библиотекой (еще не полная).    Если хочешь начать, но не знаешь как, то напиши /help или /помоги и ознакомься с набором доступных команд')

@bot.message_handler(commands=['ask','спросить']) #костыль для работы бота в группах
def ask_bot(message):
    print(f'/ask: {message.from_user.id} | {message.chat.id} | {message.text}')
    bot.send_message(message.chat.id, f'Напишите слово') 
    bot.register_next_step_handler(message, ask_run)
def ask_run(message):
    text_for_bot = message.text.lower()
    search_in_dict(text_for_bot, message)
    
    
@bot.message_handler(commands=['админ']) #для того, чтобы принудительно обновлять словарь
def admin_bot(message):
    password = message.text.replace('/админ', '').replace(' ', '')
    if password == '12121212Aa':
        bot.send_message(message.chat.id, f'Напишите "термин" @ "текст"') 
        bot.register_next_step_handler(message, dict_admin)
    else:
        print(f'Попытка доступа к панели админа {message.from_user.id}')
    
    
@bot.message_handler(commands=['help','помоги'])
def help_bot(message):
    bot.send_message(message.chat.id, 'Список доступных команд: /пример или /example - показывает как спросить определение любого термина у бота | /словарь или /dict - показать случайные термины из словаря | /дополнить или /update - предложить собственный термин и определение для бота    | /example2 или /пример2 - как обращаться к боту в общем чате | /ask или /спросить - спросить у бота термин к слову')
    
@bot.message_handler(commands=['example2','пример2'])
def example2_bot(message):
    bot.send_message(message.chat.id, f'Чтобы обращаться к боту в общем чате пишите в тексте "бот" или "@DigitalLibraryForNeftegazBot"')
    bot.send_message(message.chat.id, f'Команды из списка /help в групповом чате работают аналогично личному чату')

@bot.message_handler(commands=['example','пример'])
def example_bot(message):
    bot.send_message(message.chat.id, 'Для запроса к боту достаточно написать любой термин. К примеру напиши в любом регистре вот это:') #случайное слово из словаря для примера
    bot.send_message(message.chat.id, f'{keys_list_global[np.random.randint(0,len(keys_list_global))]}') #случайное слово из словаря для примера
    
@bot.message_handler(commands=['dict','словарь'])
def dict_bot(message):
    a = np.random.randint(0,len(keys_list_global))
    b = a+5
    if b >= len(keys_list_global):
        b = len(keys_list_global)
    bot.send_message(message.chat.id, f'Лови случаные 5 слов из словаря {keys_list_global[a:b]}') #случайные 5 терминов из словаря
    
@bot.message_handler(commands=['update','дополнить'])
def update_bot(message):
    count = len(keys_list_temp)
    print(f'{count} - кол-во запросов на обновление словаря')
    if count == 1 or count == 30 or count == 100 or count == 300 or count == 490:
        update_log()
        update_requests()
    if count > 500:
        bot.send_message(message.chat.id, f'Функция отключена, слишком много запросов от пользователей за эту сессию')
    else:
        #тут нужен фильтр на пример символов и плохих слов, чтобы не попадали в логи
        bot.send_message(message.chat.id, f'Напишите слово, которое хотите добавить или обновить у бота') 
    bot.register_next_step_handler(message,dict_update_world)


# # Ловим сообщения для бота

# In[7]:


# list_ask_bot = ['бот', 'Бот', 'БОТ', 'БоТ', 'боТ', ',jn', 'BOT','bot', 'boT', 'Bot','BoT','@DigitalLibraryForNeftegazBot']
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.chat.id == message.from_user.id: #личные сообщения
        text_for_bot = message.text.lower()
        search_in_dict(text_for_bot, message)
        print(f'ЛС: {message.from_user.id} | {message.text}')
        
    # elif message.chat.id != message.from_user.id: #общий чат
    #     for i in list_ask_bot: #перебираем варианты обращения к боту
    #         if i in message.text:
    #             text_for_bot = message.text.lower()
    #             text_for_bot = message.text.replace(i, '')
    #             print('Проверка 01')
    #             search_in_dict(text_for_bot, message)


# # Поиск термина в словаре

# In[8]:


def search_in_dict(text=0, message=0):
    if text in keys_list_global: #если слово изначально написали правильно
        id_temp = keys_list_global.index(text)
        bot.send_message(message.chat.id, f'{value_list_global[id_temp]}')
        bot.send_message(message.chat.id, f'Источник: {url_list_global[id_temp]}')
    else:
        search_deep(text, message)
        
def search_deep(text, message): #если слово изначально написали правильно - то функция поможет его найти
    text_1 = text.replace(' ', '')
    if text_1 in keys_list_global: 
        id_temp = keys_list_global.index(text_1)
        bot.send_message(message.chat.id, f'{value_list_global[id_temp]}')
        bot.send_message(message.chat.id, f'Источник: {url_list_global[id_temp]}')
        print(f'text_1 - работает {message.text}')
    else:
        text_2 = text.split(' ')
        if text_2[0] in keys_list_global: #если слово изначально написали правильно
            id_temp = keys_list_global.index(text_2[0])
            bot.send_message(message.chat.id, f'{value_list_global[id_temp]}')
            bot.send_message(message.chat.id, f'Источник: {url_list_global[id_temp]}')
            print(f'text_2 - работает {message.text}')
        else:
            local_count = 0
            text_3 = text
            for i in range(0,11):
                test_temp = text.split(str(i))
                if len(test_temp) != 1:
                    g = i
                    edited_text_3 = test_temp[0]+" "+str(g)
                    if edited_text_3 in keys_list_global: 
                        id_temp = keys_list_global.index(edited_text_3)
                        bot.send_message(message.chat.id, f'{value_list_global[id_temp]}')
                        bot.send_message(message.chat.id, f'Источник: {url_list_global[id_temp]}')
                        print(f'text_3 - работает {message.text}')
                else:
                    local_count += 1
                    if local_count > 1:
                        pass
                    else:
                        bot.send_message(message.chat.id, f'К сожалению, я не знаю этого слова.')
#                         keys_list_temp.append(message.text.lower()+"@")
#                         user_id_list_temp.append(message.from_user.id)
        
        user_id_list_temp
                    


# # Обновляем словарь

# In[9]:


def dict_update_world(message):
    user_id = message.from_user.id
    user_id_list_temp.append(category_list_temp)
    
    new_key = message.text
    if new_key in keys_list_global:
        category_list_temp.append(1)
    else:
        category_list_temp.append(0)
    
    keys_list_temp.append(new_key) #добавляем слово в словарь если написали определение
    
    bot.send_message(message.chat.id, f'Напишите определение к новому слову')
    bot.register_next_step_handler(message,dict_update_description)    

        
def dict_update_description(message):
    new_value = message.text.lower().replace(',', '')
    value_list_temp.append(new_value)
    url_list_temp.append('Пользователь telegram') #дополни возможность писать тут от куда информация
    bot.send_message(message.chat.id, f'Вы написали следующее: {keys_list_temp[-1]} - {value_list_temp[-1]}')
    bot.send_message(message.chat.id, 'Запрос на обновления словаря направлен')
    print(f'{message.from_user.id} успешно обратился к словарю: {keys_list_temp[-1]} - {message.text}')
    
def dict_admin(message):
    text = message.text.split('@')
    if len(text) != 1:
        key_admin, value_admin = text[0].lower().replace(' ',''), text[1].replace(',', '').lower()
        keys_list_global.append(key_admin)
        value_list_global.append(value_admin)
        url_list_global.append('Admin') #дополни возможность ставить источник
        update_admin()
    else:
        bot.send_message(message.chat.id, 'Ошибка, проверь наличие @')
        


# # Логика работы с БД и сохранением лога

# In[10]:


def update_log():
    print('Запуск update_log')
    df_keys = pd.DataFrame(keys_list_temp, columns=['Термин'])
    df_id = pd.DataFrame(user_id_list_temp, columns=['User.ID'])
    df_log = df_keys.join(df_id, lsuffix='_caller', rsuffix='_other')
    df_log.to_csv(logs_path, index=False, encoding='utf-16') 

def update_requests():
    print('Запуск update_requests')
    df_keys = pd.DataFrame(keys_list_temp, columns=['Термин'])
    df_values = pd.DataFrame(value_list_temp, columns=['Определение'])
    df_code = pd.DataFrame(category_list_temp, columns=['Code'])
    df_url = pd.DataFrame(url_list_temp, columns=['Ссылка'])
    
    df_temp = df_keys.join(df_values, lsuffix='_caller', rsuffix='_other')
    df_temp_2 = df_url.join(df_code, lsuffix='_caller', rsuffix='_other')
    df_requests = df_temp.join(df_temp_2, lsuffix='_caller', rsuffix='_other')
    
    df_requests.to_csv(requests_path, index=False, encoding='utf-16')
    
def update_admin():
    print('Запуск update_admin')
    df_keys = pd.DataFrame(keys_list_global, columns=['Термин'])
    df_value = pd.DataFrame(value_list_global, columns=['Определение'])
    df_url = pd.DataFrame(url_list_global, columns=['Ссылка'])
    
    df_1 = df_keys.join(df_value, lsuffix='_caller', rsuffix='_other')
    df_all = df_url.join(df_1, lsuffix='_caller', rsuffix='_other')

    df_all.to_csv(dict_path, index=False, encoding='utf-16')
    


# # Инициализация работы бота

# In[11]:


bot.polling(none_stop=True, interval=2) #none_stop - непрерывные запросы, interval - время между запросами


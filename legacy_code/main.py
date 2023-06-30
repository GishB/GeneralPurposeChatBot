#!/usr/bin/env python
# coding: utf-8

# In[2]:


import boto3
import telebot
from telebot import types # для указание типов
import os # зачем?!
import time # для работы с бд и контроля времени
import numpy as np 
import requests #Альтернатива для библиотеки urlib
import unicodedata # для работы с русскими запросами
import math #для рассчетов
import html_to_json # для анализа текста из json файла
from babel.numbers import format_decimal # для читаемого вида цифр
from io import BytesIO # для работы с mathplotlib.pyplot внутри функции
import matplotlib.pyplot as plt # для гистограмм


# In[5]:


UNIQUE_BOT_ID = 'NONE'
aws_access_key_id = 'NONE'
aws_secret_access_key = 'NONE'


# In[6]:


tconv_year = lambda x: time.strftime("%d.%m.%Y", time.localtime(x)) #Конвертация даты в читабельный вид
tconv_daily = lambda x: time.strftime("%H:%M:%S", time.localtime(x))

bot = telebot.TeleBot(UNIQUE_BOT_ID)

# ---------------- Ловим команды для бота ----------------
@bot.message_handler(commands=['start','начать','привет','hello'])
def start_bot(message):
    bot.send_message(message.chat.id, f'Здравствуй, {message.from_user.username}! Я бот Нефтезнайка версии 0.3')
    bot.send_photo(message.chat.id, 'https://storage.yandexcloud.net/files-for-nefteznayka/Nefteznayka.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=YCAJEwQTooTrz4ur8xxDEaXeJ%2F20220723%2Fru-central1%2Fs3%2Faws4_request&X-Amz-Date=20220723T195313Z&X-Amz-Expires=3600&X-Amz-Signature=36DF532B2DCADE434C4775344F9D0A62EEE989C7E4BF1C320929E8611F0A3D97&X-Amz-SignedHeaders=host')
    # bot.send_message(message.chat.id, "В данной версии реализована возможность пользоваться цифровой библиотекой (еще не полная). \n   Если хочешь начать, но не знаешь как, то напиши /help или <pre><code class='language-python'>/помоги</code></pre> и ознакомься с набором доступных команд", parse_mode="HTML")
    keyboard = types.ReplyKeyboardMarkup()
    button_1 = types.KeyboardButton(text="/ask")
    keyboard.add(button_1)
    bot.send_message(message.chat.id,"В данной версии реализована возможность пользоваться цифровой библиотекой (еще не полная). \n   Если хочешь начать, но не знаешь как, то напиши /help или <pre><code class='language-python'>/помоги</code></pre> и ознакомься с набором доступных команд", parse_mode="HTML", reply_markup=keyboard)

##########################################################
#________________________________________________________#
##########################################################

def request_link(link, headers):
    response = requests.get(link, headers=headers)
    mystr = response.content
    mystr = mystr.decode("utf8")
    json_data = html_to_json.convert(mystr)
    return json_data

def plot_hist(results, message):
    session = boto3.session.Session()
    s3 = session.client(
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net',
        region_name = 'ru-central1',
        aws_access_key_id = aws_access_key_id,
        aws_secret_access_key = aws_secret_access_key
    )
    fig, ax = plt.subplots()
    ax.hist(results)
    ax.grid()
    ax.set_xlabel('Стоимость торгов в руб. (le6 = 1 миллион)',
              fontsize = 15,    #  размер шрифта
              color = 'red')
    ax.set_ylabel('Кол-во торгов в усл. ед.',
              fontsize = 15,
              color = 'red')
    b = BytesIO()
    plt.savefig(b, format='png')
    b.seek(0)
    plt.close()
    key_save=str(message.message_id)+'_'+str(message.from_user.id)+'_img.png'
    s3.put_object(Bucket='cloud-files-public', Key=key_save, Body=b, StorageClass='COLD')
    bot.send_photo(message.chat.id, 'https://storage.yandexcloud.net/cloud-files-public/'+key_save)
    # bot.send_photo(message.chat.id, plt.show(), reply_to_message_id=message.message_id)

def registered_trades(url, clean_text, headers, message):
    output_json = request_link(url+clean_text+'&recordsPerPage=_10', headers)
    try:
        number_registered_trades = int(output_json['html'][0]['body'][0]['form'][0]['section'][1]['div'][0]['div'][0]['div'][0]['div'][0]['div'][1]['_value'].split(' ')[0])
    except:
        number_registered_trades = int(unicodedata.normalize("NFKD",(output_json['html'][0]['body'][0]['form'][0]['section'][1]['div'][0]['div'][0]['div'][0]['div'][0]['div'][1]['_value'].split(' ')[1])).replace(' ',''))
    if number_registered_trades >= 200:
        number_registered_trades = 200
    return number_registered_trades

def mining_trades_loop(number_pages, url, request, message, headers):
    prices = []
    count_none = 0
    for i in range(1, number_pages+1):
        new_link = url+request.replace(" ","+")+('&pageNumber=')+str(i)+'&recordsPerPage=_100' #создаем новую ссылку с страницей:
        output_json = request_link(new_link, headers)
        for g in range(100):
            try:
                if len(output_json['html'][0]['body'][0]['form'][0]['section'][1]['div'][0]['div'][0]['div'][0]['div'][2]['div'][g]['div'][0]['div'][1]['div'][0]) != 2:
                    count_none+=1
                else:
                    price_string = output_json['html'][0]['body'][0]['form'][0]['section'][1]['div'][0]['div'][0]['div'][0]['div'][2]['div'][g]['div'][0]['div'][1]['div'][0]['div'][1]['_value']
                    clean_text = unicodedata.normalize("NFKD",price_string)
                    if '₽' not in clean_text:
                        price_int = int(clean_text.replace(' ','').replace('₽','').split(',')[0])*60 #60 - курс евро и доллара
                    else:
                        price_int = int(clean_text.replace(' ','').replace('₽','').split(',')[0])
                    prices.append(price_int)
            except:
                pass
    price_max = max(prices)
    price_min = min(prices)
    bot.send_message(message.chat.id, 'посчитал успешно...')
    return sum(prices), price_max, price_min, np.mean(prices), len(prices) + count_none, count_none, prices

def show_results(results, url, request, message):
    bot.send_message(message.chat.id, f'Суммарная сумма торгов: {format_decimal(results[0], locale="ru_RU")}                                        Максимальная сумма: {format_decimal(results[1], locale="ru_RU")}                                        Минимальная сумма: {format_decimal(results[2], locale="ru_RU")}                                        Средняя сумма: {format_decimal(int(results[3]), locale="ru_RU")}                                        Кол-во сделок: {results[4]}                                        Кол-во торгов с неизвестной суммой сделки: {results[5]}                                        \n Ссылка: {url+unicodedata.normalize("NFKD",request).replace(" ","+")}') 

@bot.message_handler(commands=['test','special_function'])
def analysis(message):
    bot.send_message(message.chat.id, f'    Запрос будет обработан на сайте гос. закупок - https://zakupki.gov.ru: \n    Введите текст запроса ниже:')
    bot.register_next_step_handler(message, run_analysis)

def run_analysis(message):
    if message.text != '/cancel':
        headers = {'USER-AGENT': 'Mozilla/5.0 (iPad; U; CPU OS 3_2_1 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Mobile/7B405'}
        url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?searchString="
        request = message.text
        clean_text = unicodedata.normalize("NFKD",request).replace(" ","+")
        bot.send_message(message.chat.id, '*Ожидайте примерно 2 минуты*')
        number_registered_trades = registered_trades(url, clean_text, headers, message)

        if number_registered_trades == 0:
            bot.send_message(message.chat.id, 'Ничего не найдено по этому запросу')
            bot.send_message(message.chat.id,f" Ссылка: {url+unicodedata.normalize('NFKD',request).replace(' ','+')}")

        else:
            len_page_trades = 100
            number_pages = math.ceil(number_registered_trades/len_page_trades)
            bot.send_message(message.chat.id, 'начал рассчет...')
            results = mining_trades_loop(number_pages, url, request, message, headers)
            show_results(results, url, request, message)
            plot_hist(results, message)
    else:
        pass
#################################################################################
#_------------------------------------------------------------------------------#
#################################################################################

@bot.message_handler(commands=['help','помоги'])
def help_bot(message):
    bot.send_message(message.chat.id, "Список доступных команд: \n <pre><code class='language-python'>/пример</code></pre> или /example - показывает как спросить определение любого термина у бота \n <pre><code class='language-python'>/словарь</code></pre> или /dict - показать термины из словаря     \n /example2 или <pre><code class='language-python'>/пример2</code></pre> - как обращаться к боту в общем чате \n /ask или <pre><code class='language-python'>/спросить</code></pre> - спросить у бота термин к слову \n /admin или <pre><code class='language-python'>/админ</code></pre> - доступ к панели администратора     \n /register или <pre><code class='language-python'>/регистрация</code></pre> - для полной регистрации в чат-боте     \n /eat или <pre><code class='language-python'>/еда</code></pre> - для веб-сервиса 'где пообедать?'     \n /play или <pre><code class='language-python'>/играть</code></pre> - для игры 'Нефтезмейка'     \n /test или /special_function - для анализа гос. закупок на сайте ЕИС", parse_mode="HTML")

@bot.message_handler(commands=['register','регистрация']) #запрос в словарь
def register(message):
    bot.send_message(message.chat.id, f'Функция в разработке 31.08.2022') 


@bot.message_handler(commands=['play','играть']) #запрос в словарь
def play(message):
    bot.send_message(message.chat.id, f'🤖')     
    bot.send_message(message.chat.id, f'Коллега "Нефтезмейка" готов с тобой поиграть. Напишу ему - @NeftezmeikaBot') 

@bot.message_handler(commands=['кушать','где поесть','gdepoobedat','где пообедать','eat','еда','eda']) #запрос в словарь
def play(message):
    bot.send_message(message.chat.id, f'🕵️')     
    bot.send_message(message.chat.id, f'Давай проверим сайт вместе? https://gdepoobedat.ru') 

@bot.message_handler(commands=['ask','спросить']) #запрос в словарь
def ask_bot(message):
    bot.send_message(message.chat.id, f'Напишите слово') 
    bot.register_next_step_handler(message, ask_run)

@bot.message_handler(commands=['example','пример'])
def example_bot(message):
    bot.send_message(message.chat.id, 'Для запроса к боту достаточно написать /ask и следующим сообщением любой термин из словаря /dict. \n К примеру напиши в любом регистре вот это:') #случайное слово из словаря для примера
    bot.send_message(message.chat.id, '/ask')
    bot.send_message(message.chat.id, 'Александр') #случайное слово из словаря для примера

@bot.message_handler(commands=['dict','словарь'])
def dict_bot(message):
 #случайное слово из словаря для примера
    temp_words = take_some_words(9)
    bot.send_message(message.chat.id, f'Попробуйте следующий список терминов: {temp_words}') #случайные 5 терминов из словаря

@bot.message_handler(commands=['example2','пример2'])
def example2_bot(message):
    bot.send_message(message.chat.id, f'Для обращения к боту в общем чате пишите /ask@Nefteznayka, следующим сообщением ваш вопрос')
    bot.send_message(message.chat.id, '/ask@Nefteznayka')
    temp_word = take_some_words(2)
    bot.send_message(message.chat.id, f'{temp_word}')
    
# list_discription_temp = []
@bot.message_handler(commands=['updatedict']) #запрос в словарь
def updatedict(message):
    # bot.send_message(message.chat.id, f'Функция в разработке и работает некорректно - 01.09.2022')
    bot.send_message(message.chat.id, 'Напишите термин, определение и ссылку (смотрите кнопки под чатом):')
    keyboard = types.ReplyKeyboardMarkup()
    button_1,button_2 = types.KeyboardButton(text="/термин"),    types.KeyboardButton(text="/cancel")
    keyboard.add(button_1).add(button_2)
    bot.send_message(message.chat.id, '/cancel для выхода из цикла', reply_markup=keyboard)     
    bot.register_next_step_handler(message, next_update_dict)

def next_update_dict(message):
    if message.text == '/cancel':
        pass
    if message.text == '/термин':
        bot.send_message(message.chat.id, 'Напишите термин:', reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, next_update_dict_2_0)   
    elif message.text == '/определение':
        bot.send_message(message.chat.id, 'Напишите определение к термину', reply_markup=telebot.types.ReplyKeyboardRemove())  
        bot.register_next_step_handler(message, next_update_dict_2_1) 
    elif message.text == '/ссылка на определение':
        bot.send_message(message.chat.id, 'Укажите ссылку на определение', reply_markup=telebot.types.ReplyKeyboardRemove()) 
        bot.register_next_step_handler(message, next_update_dict_2_2) 
    else:
        bot.send_message(message.chat.id, 'Исключение в алгоритме. Попробуйте еще раз')
        pass
         
def next_update_dict_2_0(message):
    if message.text == '/cancel':
        pass
    else:
        dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
        region_name = 'ru-central1',
        aws_access_key_id = aws_access_key_id,
        aws_secret_access_key = aws_secret_access_key)         
        table = dynamodb.Table('update_dict_db_test')
        response = table.put_item(
            Item =
            {
            'user_id': str(message.from_user.id),
            'world': str(message.text),
            'time': str(tconv_daily(message.date)),
            'date_year': str(tconv_year(message.date))
            }) 
        keyboard = types.ReplyKeyboardMarkup()
        button_2, button_3 =        types.KeyboardButton(text="/определение"),        types.KeyboardButton(text="/cancel")
        keyboard.add(button_2).add(button_3)
        bot.send_message(message.chat.id, '/cancel для выхода из цикла', reply_markup=keyboard)
        bot.send_message(message.chat.id, 'Термин был записан')     
        bot.register_next_step_handler(message, next_update_dict)

def next_update_dict_2_1(message):
    if message.text == '/cancel':
        pass
    else:
        dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
        region_name = 'ru-central1',
        aws_access_key_id = aws_access_key_id,
        aws_secret_access_key = aws_secret_access_key)          
        table = dynamodb.Table('update_dict_db_test')
        termin = table.get_item(Key={'user_id': str(message.from_user.id)})['Item']['world']
        response = table.put_item(
            Item=
            {
            'user_id': str(message.from_user.id),
            'world': str(termin),
            'description': str(message.text),
            'time': str(tconv_daily(message.date)),
            'date_year': str(tconv_year(message.date))
            }) 
        keyboard = types.ReplyKeyboardMarkup()
        button_2, button_3 =        types.KeyboardButton(text="/ссылка на определение"),        types.KeyboardButton(text="/cancel")
        keyboard.add(button_2).add(button_3)
        bot.send_message(message.chat.id, '/cancel для выхода из цикла', reply_markup=keyboard)     
        bot.register_next_step_handler(message, next_update_dict)

def next_update_dict_2_2(message):
    if message.text == '/cancel':
        pass
    else:
        dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
        region_name = 'ru-central1',
        aws_access_key_id = aws_access_key_id,
        aws_secret_access_key = aws_secret_access_key)          
        table = dynamodb.Table('update_dict_db_test')
        response_past = table.get_item(Key={'user_id': str(message.from_user.id)})['Item']
        termin = response_past['world']
        description = response_past['description']
        response = table.put_item(
            Item={
            'user_id': str(message.from_user.id),
            'link': str(message.text),
            'world': str(termin),
            'description': str(description),
            'time': str(tconv_daily(message.date)),
            'date_year': str(tconv_year(message.date))
            }) 
        bot.send_message(message.chat.id, 'Ссылка на термин была записана, спасибо 😘')     



#\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
#---------------------------------Панель админа-----------------------------------------------
@bot.message_handler(commands=['admin','админ','создатель']) #запрос в словарь
def admin(message):
    dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
    region_name = 'ru-central1',
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key)
    users_dict = dynamodb.Table('admin_users_bd').scan(AttributesToGet=['user_id'])['Items']
    list_id = []
    for i in range(len(users_dict)):
        temp_id = str(users_dict[i]['user_id'])
        list_id.append(temp_id)
    if str(message.from_user.id) in list_id:
        log_admin(message)
        keyboard = types.ReplyKeyboardMarkup()
        button_1, button_2, button_3 = types.KeyboardButton(text="Оповещение пользователей"),types.KeyboardButton(text="Обновление списка известных пользователей"),types.KeyboardButton(text="Test buttom")
        keyboard.add(button_1).add(button_2).add(button_3)
        bot.send_message(message.chat.id,'Доступ к панели админа открыт', reply_markup=keyboard)
        bot.register_next_step_handler(message,bottom_admin_run)
    else:
        pass
    
def log_admin(message):
    dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
    region_name = 'ru-central1',
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key)

    table = dynamodb.Table('admin_users_bd')
    response = table.put_item(
        Item={ 
        'user_id': str(message.from_user.id),
        'last_message': str(message.text),
        'time': str(tconv_daily(message.date)),
        'date': str(tconv_year(message.date)),
        })

def bottom_admin_run(message):
    if message.text == 'Оповещение пользователей':
        keyboard = types.ReplyKeyboardMarkup()
        button_1, button_2 = types.KeyboardButton(text="Сценарий - 'произвольное сообщение для всех'"),types.KeyboardButton(text="Сценарий - 'А знаете ли вы это слово?'")
        keyboard.add(button_1).add(button_2)
        bot.send_message(message.chat.id,'Какой сценарий оповещения нужен?', reply_markup=keyboard)
        bot.register_next_step_handler(message,bottom_notifications)
    elif message.text == 'Обновление списка известных пользователей':
        bot.send_message(message.from_user.id, 'Функция в разработке 30.08.2022', reply_markup=telebot.types.ReplyKeyboardRemove())
#     elif message.text == 'Test buttom':
#         bot.send_message(message.from_user.id, 'Test working...', reply_markup=telebot.types.ReplyKeyboardRemove())
#         bot.send_message(507244619, 'Тестовое сообщение от бота - необходима обратная связь @Aleksandr_Driller')
#         bot.send_message(message.from_user.id, 'Test done correctly. Message delivered')
    else:
        bot.send_message(message.from_user.id, 'К сожалению, бот не понял этот запрос', reply_markup=telebot.types.ReplyKeyboardRemove())
        
def bottom_notifications(message):
    if message.text == "Сценарий - 'произвольное сообщение для всех'":
        bot.send_message(message.from_user.id, 'Введите текст для оповещения', reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message,custom_notification_all_users)

    elif message.text == "Сценарий - 'А знаете ли вы это слово?'":
        list_id_users = ask_users_id_bd() #необходимо знать уникальные id пользователей
        number_users = len(list_id_users)
        list_random_words = take_some_words(number_users) #необходимо знать пару терминов из словаря
        number_words = len(list_random_words)
        bot.send_message(message.from_user.id, 'Бот начал рассылку сообщений. Не трогайте его пару минут.', reply_markup=telebot.types.ReplyKeyboardRemove())
        for i in list_id_users:
            temp_world = list_random_words[np.random.randint(number_words)]
            keyboard = types.ReplyKeyboardMarkup()
            button_1 = types.KeyboardButton(text=f"{temp_world}")
            keyboard.add(button_1)
            random_path_number = np.random.randint(3)
            try:
                if random_path_number == 1:
                    bot.send_message(int(i),f'Привет от бота🤖! Я к тебе тут с небольшим вопросом - ты справишься. \n Знаешь значение термина - {temp_world}?🤖 \n \n Кликай на кнопку и я помогу тебе в любом случае 👌', reply_markup=keyboard)
                elif random_path_number == 2:
                    bot.send_message(int(i),f'Не ожидал? А вот и я - 🤖! У меня к тебе риторический вопрос. \n Знаешь значение термина - {temp_world}?🤖 \n Кликай на кнопку и я помогу тебе в любом случае', reply_markup=keyboard)
                    bot.send_message(int(i), '🦾')
                elif random_path_number == 3:
                    bot.send_message(int(i),f'😀 \n \n - У меня к тебе есть риторический вопрос. \n Знаешь значение термина - {temp_world}? \n \n Кликай на кнопку и я помогу тебе узнать 😘', reply_markup=keyboard)
                    bot.send_message(int(i), '😘')
                else:
                    bot.send_message(int(i), '👀')
                    bot.send_message(int(i),f'Бот проснулся и захотел именно тебе задать вопрос. \n Знаешь значение термина - {temp_world}? \n \n Кликай на кнопку, чтобы узнать ответ 😘', reply_markup=keyboard)
            except:
                time.sleep(0.5)

    else:
        bot.send_message(message.from_user.id, 'К сожалению, бот не понял этот запрос.', reply_markup=telebot.types.ReplyKeyboardRemove())

def custom_notification_all_users(message):
    list_id_users = ask_users_id_bd() #необходимо знать уникальные id пользователей
    number_users = len(list_id_users)
    bot.send_message(message.from_user.id, 'Бот начал рассылку сообщений. Не трогайте его пару минут.', reply_markup=telebot.types.ReplyKeyboardRemove())
    for i in list_id_users:
        try:
            bot.send_message(int(i), f'{message.text}')
        except:
            time.sleep(0.5)

def ask_notification_id_bd(id_admin):
    dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
    region_name = 'ru-central1',
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key
    )
    table = dynamodb.Table('notification_id_bd').scan(AttributesToGet=['user_id','text'])['Items']
    list_id = []
    for i in range(len(table)):
        temp_id = str(table[i]['user_id'])
        if temp_id == str(id_admin):
            return table[i]['text']
        else:
            pass


def ask_users_id_bd():
    dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
    region_name = 'ru-central1',
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key
    )
    table = dynamodb.Table('unique_users_id').scan(AttributesToGet=['user_id'])['Items']
    list_id = []
    for i in range(len(table)):
        temp_id = str(table[i]['user_id'])
        if temp_id not in list_id:
            list_id.append(temp_id)
    return list_id

def take_some_words(number):
    dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
    region_name = 'ru-central1',
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key)
    
    dict_of_words = dynamodb.Table('oil_dict').scan(AttributesToGet=['world'])['Items']
    random_numbers_of_words_toget = np.random.randint(1, number) 
    number_of_dict_words = len(dict_of_words)
    random_worlds_list = []
    for i in range(random_numbers_of_words_toget):
        random_worlds_list.append(dict_of_words[np.random.randint(number_of_dict_words)]['world'])
    return random_worlds_list
    
#\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
#_--------------------------------Викторина---------------------------------------------------
@bot.message_handler(commands=['event','событие']) #запрос в словарь
def event(message):
    bot.send_message(message.chat.id, f'Функция в разработке. 13.08.2022') 
    bot.send_message(message.chat.id, f'Вы хотите участвовать в викторине?')
    #предложить пользователю варианты выбора на кнопках ДА и НЕТ, или словами да и нет, хочу, конечно
    bot.register_next_step_handler(message, event_reg)
def event_reg(message):
    bot.send_message(message.chat.id, f'Формируем вопрос для пользователя из актуальной викторины. \n    Кто первым открыл Америку?')
    #варианты выбора в виде четырех кнопок 
    #сохраняем выбор пользователя и записываем в БД (всегда сохраняем последний ответ пользователя)
    bot.send_message(message.chat.id, f'Ваш ответ условно записан в БД.')
    bot.send_message(message.chat.id, f'Не забывайте регистрироваться в чат-боте /register если хочите получить приз')
    

# ---------------- Ловим сообщение от пользователя в личном чате -------------------------------------
@bot.message_handler(content_types=['text'])
def get_text_messages(message): #take a message from an user / ловим message поступившее боту от пользователя
    if message.chat.id == message.from_user.id: #private bot dialog / личные сообщения к боту
        if message.text.lower().replace(' ','') == 'привет':
            stickers_list = ['👋','🕺','🕵️','🖖','👨‍🚀','🧞‍♂️','🧞','🧞‍♀️']
            bot.send_message(message.chat.id, f'{stickers_list[np.random.randint(0,7)]}')
        elif message.text.lower().replace(' ','') == 'чтотыумеешь?':
            bot.send_message(message.chat.id, f'Окей, посмотри на список доступных команд /help или попробуй написать /example')
            help_bot(message)
        else:
            ask_run(message)
    else:
        pass #сообщения в общем чате не интересны

#----------------- Ловим файлы и голосовые сообщения от пользователей ---------------------------------
@bot.message_handler(content_types=['document', 'audio'])
def handle_docs_audio(message):
    bot.send_message(message.chat.id, f'С такими данными бот еще работать не умеет - напишите /help или /example')

# ---------------- Читаем словарь ---------------------------------------------------------------------
def ask_run(message):
    bot.send_message(message.from_user.id, 'Выполняю поиск🤖', reply_markup=telebot.types.ReplyKeyboardRemove())
    update_user_request(message)
    text_temp = message.text.lower().replace(' ','').replace('!','').replace('?','').replace('.','').replace('`','')
   
    dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
    region_name = 'ru-central1',
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key)

    table = dynamodb.Table('oil_dict')
    response = table.get_item(Key={'world': text_temp})
    if 'Item' not in response:
        bot.send_message(message.chat.id, f'К сожалению, пока такого не знаю. Однако, ты можешь мне помочь и добавить новое слово в словарь \n /updatedict ☺️')
    else:
        bot.send_message(message.chat.id, response['Item']['description'])
        bot.send_message(message.chat.id, response['Item']['link'])

#---------------Сохраняем запрос пользователя к боту в личном чате-------------------------------
def update_user_request(message):

    dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='https://docapi.serverless.yandexcloud.net/ru-central1/b1g0no91baqs47rea2is/etn9ic5949ep5rukiq6r',
    region_name = 'ru-central1',
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key)
   
    table = dynamodb.Table('user_messages_db')
    response = table.put_item(
        Item={
        'unique_message_id': str(message.message_id)+str(message.from_user.id),  
        'user_id': str(message.from_user.id),
        'text': str(message.text),
        'time-daily': str(tconv_daily(message.date)),
        'time-year': str(tconv_year(message.date)),
        })


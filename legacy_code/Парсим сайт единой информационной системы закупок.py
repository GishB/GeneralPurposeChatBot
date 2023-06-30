#!/usr/bin/env python
# coding: utf-8

# # Подгружаем необходимые библиотеки

# In[1]:


import requests #Альтернатива для библиотеки urlib
import unicodedata # для работы с русскими запросами
import math #для рассчетов
import numpy as np #для генерации рандомных чисел (совместно с библиотекой time)
import html_to_json 
import locale # для работы с цифрами в удобном виде
import matplotlib.pyplot as plt
from io import BytesIO
from babel.numbers import format_decimal


if __name__ == '__main__':
    url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?searchString=" # содержит html с списком всех вхождений слов в dictionary
    request = str(input())
    standart_url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?searchString=%D1%82%D0%B5%D0%BB%D0%B5%D0%BC%D0%B5%D1%82%D1%80%D0%B8%D1%8F+%D1%81%D0%BA%D0%B2%D0%B0%D0%B6%D0%B8%D0%BD&morphology=on&search-filter=%D0%94%D0%B0%D1%82%D0%B5+%D0%BE%D0%B1%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F&pageNumber=2&sortDirection=false&recordsPerPage=_10&showLotsInfoHidden=false&savedSearchSettingsIdHidden=&sortBy=UPDATE_DATE&fz44=on&fz223=on&af=on&ca=on&pc=on&pa=on&placingWayList=&selectedLaws=&priceFromGeneral=&priceFromGWS=&priceFromUnitGWS=&priceToGeneral=&priceToGWS=&priceToUnitGWS=&currencyIdGeneral=-1&publishDateFrom=&publishDateTo=&applSubmissionCloseDateFrom=&applSubmissionCloseDateTo=&customerIdOrg=&customerFz94id=&customerTitle=&okpd2Ids=&okpd2IdsCodes=" #содержит ссылку до каждого слова в словаре


# # Пишем основные функции для парсинга

# In[4]:


def request_link(link, headers):
    response = requests.get(link, headers=headers)
    mystr = response.content
    mystr = mystr.decode("utf8")
    json_data = html_to_json.convert(mystr)
    return json_data

def registered_trades(url, clean_text, headers):
    output_json = request_link(url+clean_text+'&recordsPerPage=_10', headers)
    try:
        number_registered_trades = int(output_json['html'][0]['body'][0]['form'][0]['section'][1]['div'][0]['div'][0]['div'][0]['div'][0]['div'][1]['_value'].split(' ')[0])
    except:
        number_registered_trades = int(unicodedata.normalize("NFKD",(output_json['html'][0]['body'][0]['form'][0]['section'][1]['div'][0]['div'][0]['div'][0]['div'][0]['div'][1]['_value'].split(' ')[1])).replace(' ',''))
    if number_registered_trades >= 5000:
        number_registered_trades = 1000
    return number_registered_trades

def mining_trades_loop(number_pages, url, request, headers):
    prices = []
    count_none = 0
    for i in range(1, number_pages+1):
        new_link = url+request.replace(" ","+")+('&pageNumber=')+str(i)+'&recordsPerPage=_100' #создаем новую ссылку с страницей:
        output_json = request_link(new_link, headers)
        print(i)
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
                print(g)
    price_max = max(prices)
    price_min = min(prices)
    return sum(prices), price_max, price_min, np.mean(prices), len(prices)+count_none, count_none, prices

def plot_hist(results):
    fig, ax = plt.subplots()
    ax.hist(results)
    ax.grid()
    ax.set_xlabel('Стоимость торгов',
              fontsize = 15,    #  размер шрифта
              color = 'red')
    ax.set_ylabel('Кол-во торгов в усл. ед.',
              fontsize = 15,
              color = 'red')
    plt.show()
    
    
def show_results(results):
    print(f'Суммарная сумма торгов за все время: {format_decimal(results[0], locale="ru_RU")} ₽')
    print(f'Максимальная сумма торгов за все время: {format_decimal(results[1], locale="ru_RU")}')
    print(f'Минимальная сумма торгов за все время: {format_decimal(results[2], locale="ru_RU")}')
    print(f'Средняя сумма торгов за все время: {format_decimal(results[3], locale="ru_RU")}')
    print(f'Кол-во торгов за все время: {results[4]}')
    print(f'Кол-во торгов с неизвестной суммой сделки: {results[5]}')
    print(f'Ссылка: {url+unicodedata.normalize("NFKD",request).replace(" ","+")}')


# # Нормализуем ссылку для парсинга и скрываем бота ложным headers

# In[5]:

if __name__ == '__main__':
    headers = {'USER-AGENT': 'Mozilla/5.0 (iPad; U; CPU OS 3_2_1 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Mobile/7B405'}
    clean_text = request.replace(" ","+")


# # Парсим сайт

# In[3]:


if __name__ == '__main__':
    number_registered_trades = registered_trades(url, clean_text, headers)
    if number_registered_trades == 0:
        get_ipython().run_line_magic('pinfo', 'number_registered_trades')
    else:
        len_page_trades = 100
        number_pages = math.ceil(number_registered_trades/len_page_trades)
        results = mining_trades_loop(number_pages, url, request, headers)
        _ = show_results(results)
        plot_hist(results[-1])    




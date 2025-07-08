# Telegram Bot - UnionHelperBot

 This is a telegram bot which can interact with AI models via YandexCloud API.
 Baseline idea is to help workers find related info from documents. It is powered by ***YandexGPTAPI***.

tg link:
> https://t.me/HelperUnionBot
 
 - To start interact you need just to type /start or /начать.
 - If you want just to know something just start to type and you easily find out your answer.

 ## How to Start?

**Developer guide**
   1. You have to define API credentials for Telegram and YandexAPI at **.env** file! As well to feed data into chromadb COLLECTION_NAME.
   2. `` git clone https://github.com/GishB/GeneralPurposeTelegramBOT ``
   3. `` pip install -e .``
   4. `` sudo docker run -d -p 6379:6379 redis/redis-stack:latest``
   5. `` sudo docker run -v ./chroma-data:/data -p 32000:8000 -d chromadb/chroma`` 
   6. `` cd ./src/UnionChatBot``
   7. `` python3 main.py``

**Docker Compose setting up**

Minimum setup from docker-compose file:
 - 3 CPU
 - 6 GB

1. You have to define API credentials for YandexAPI at **.env.prod** file! As well you will have to feed data into chromadb COLLECTION_NAME.


2. Start docker images.
```commandline
 sudo docker compose up -d
```

3. HERE WE GO!
```commandline
curl -X 'POST' \
  'http://127.0.0.1:8000/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Какой коллективный договор действует на предприятии? Хочу знать общую информацию по КД.",
  "user_id": "0",
  "request_id": "md5hash"
}'

```

 ## Ideal chatbot functions:
 
  1. Interact with user via text and keep in memory all chat history.
  2. Interact with user via audio and return result as well in audio text.
  3. Keep up to date info related to user life in Vector DB.
  4. Ability to keep in memory user custom task and control it progress.
  5. Ability to save all user experience between platforms and ChatBot. For example it can be user laptop app, social media.
  6. Provide links for users for any answers
  7. ??

## **TO DO LIST:**
 - [x] Adapater for YandexGPTAPI.
 - [x] Redis Caching (Redis Adapter class)
 - [x] ChromaDB for RAG system (ChromaAdapter class)
 - [x] RerankingAPI for selected documents.
 - [x] ChatHistoryManager (based on Redis).
 - [ ] QueryHelpManager (rewrite or modify user query in case of problems with query)
 - [ ] Transform Audio request and model output to audio\text to interact with user.
 - [ ] Docker Image
 - [ ] github workflow for CI.
 - [ ] README setup locally .
 - [ ] Async libraries to interact with users instead of telegrambotapi.

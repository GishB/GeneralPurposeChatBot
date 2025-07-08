# UnionHelperBot

 This is a repo for general purpose chatbot which can interact with AI models via YandexCloud API.
 Baseline idea is to help user find related info from documents. It is powered by ***YandexGPTAPI***, Redis and ChromaDB.

If you would like to check this bot go to tg link (sometimes i will run this for tests):
> https://t.me/HelperUnionBot
 
 - To start interact you need just to type /start or /начать.
 - If you want just to know something just start to type and you easily find out your answer.

 ### Who use this ChatBot template?

 This backend logic used at a local WorkerUnion organization.
 ### How to Start?

**Developer guide**

``This is useful if you would like to test telegram API.``
   1. You have to define API credentials for Telegram and YandexAPI at **.env** file! As well to feed data into chromadb COLLECTION_NAME.
   2. `` git clone https://github.com/GishB/GeneralPurposeTelegramBOT ``
   3. `` pip install -e .``
   4. `` sudo docker run -d -p 6379:6379 redis/redis-stack:latest``
   5. `` sudo docker run -v ./chroma-data:/data -p 32000:8000 -d chromadb/chroma`` 
   6. `` cd ./src/UnionChatBot``
   7. `` python3 main.py``

**Docker Compose setting up**

``If you would like just to start you own chatbot API based on this solution.``

Minimum setup from docker-compose file (can be changed by user manually):
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
  "query": "Hello! How are you? What the latest news you know about workerunion life?",
  "user_id": "0",
  "request_id": "md5hash"
}'
```

If you woild like to change default prompt you will have 3 options.

1. The first option is to add to POST request your own prompt!
2. The second option is to change default prompt file when you build your own image for chat-bot.
3. The third option is to change .env.prod default name file which you would like to use by default. (the problem here you will need to build image from scratch)


 ### Ideal chatbot functions:
 
  1. Interact with user via text and keep in memory all chat history.
  2. Interact with user via audio and return result as well in audio text.
  3. Keep up to date info related to user life in Vector DB.
  4. Ability to keep in memory user custom task and control it progress.
  5. Ability to save all user experience between platforms and ChatBot. For example it can be user laptop app, social media.
  6. Provide links for users for any answers
  7. ??

### **TO DO LIST:**
 - [x] Adapater for YandexGPTAPI.
 - [x] Redis Caching (Redis Adapter class)
 - [x] ChromaDB for RAG system (ChromaAdapter class)
 - [x] RerankingAPI for selected documents.
 - [x] ChatHistoryManager (based on Redis).
 - [ ] QueryHelpManager (rewrite or modify user query in case of problems with query)
 - [ ] Transform Audio request and model output to audio\text to interact with user.
 - [x] Docker Image
 - [ ] github workflow for CI/CD.
 - [X] README setup locally .
 - [X] Async libraries to interact with users instead of telegrambotapi.

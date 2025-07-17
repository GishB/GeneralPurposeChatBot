# GeneralPurposeChatBot

 This is a repo for general purpose chatbot which can interact with AI models via YandexCloud API.
 Baseline idea is to help developers to create ChatBotAPI + RAG for users who like to find related info from documents. It is powered by ***YandexGPTAPI***, Redis and ChromaDB.

If you would like to check this bot go to tg link (sometimes i will run this for tests):
> https://t.me/HelperUnionBot
 
 - To start interact you need just to type /start or /начать.
 - If you want just to know something just start to type and you easily find out your answer.

 ### How to Start?

**Developer guide**

``This is useful if you would like to test telegram API.
You will up two DataBases for this (Redis and ChromaDB).``
   1. You have to define API credentials for Telegram and YandexAPI at **.env** file!
      - YandexCloud tutorial: https://yandex.cloud/en/docs/iam/quickstart-sa
   2. `` sudo docker run -v ./chroma-data:/data -p 32000:8000 -d chromadb/chroma`` 
   3. `` git clone https://github.com/GishB/GeneralPurposeTelegramBOT ``
   4. Load your *.md files into dir data -> ./src/data
   5.  `` pip install .``
   6. Load .env file -> `` source .env``
   7. `` cd src/scripts | python3 load_data_to_chroma.py``
   8. `` sudo docker run -d -p 6379:6379 redis/redis-stack:latest``
   9. `` cd ./src/telegram | python3 main.py``

**Docker Compose setting up**

``If you would like just to start you own chatbot API based on my solution.``

Minimum setup from docker-compose file (can be changed by user manually):
 - 4 CPU
 - 6.5 GB

1. You have to define API credentials for YandexAPI at **.env.prod** file! 
 
 - YandexCloud tutorial: https://yandex.cloud/en/docs/iam/quickstart-sa

2. Start docker images from project dir.
```commandline
 sudo docker compose up -d
```

3. Load your *.md files into dir data -> ./src/data
```commandline
wget from somewhere!
```

4. Feed data into ChromaDB <COLLECTION_NAME>.

```commandline
cd src/scripts
python3 load_data_to_chroma.py
```
5. HERE WE GO!
```commandline
curl -k -X 'POST' \
  'https://localhost/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Token: QweuqqwQEW312eqwewWEWEEADAsd-WEQQ1231273787' \
  -d '{
  "query": "Hello! How are you? What the latest news you know about workerunion life?",
  "user_id": "0",
  "request_id": "md5hash"
}'
```

The answer will be -->
```
{"status":"success","response":"Hello! I'm doing well, thank you. Regarding the latest news about the worker union life at AO \"Nevinnomysskiy Azot\", the collective agreement currently in force covers the period from 2024 to 2026. The agreement can be extended for a period of up to three years, provided that the decision to extend is made no later than three months before the current agreement expires.","user_id":"0","request_id":"md5hash"}
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
 - [X] Nginx to control interactions.
 - [X] github workflow for CI/CD.
 - [X] README setup locally .
 - [X] Async libraries to interact with users instead of telegrambotapi.
 - [ ] Add options to use user defined prompt files via mount if we use Docker Compose? 
 -  [ ] Fix Reranker logic.
 -  [ ] Baseline checker for generated text.
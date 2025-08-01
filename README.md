# GeneralPurposeChatBot

 This is a repo for general purpose chatbot which can interact with AI models via YandexCloud API.
 Baseline idea is to help developers to create ChatBotAPI + RAG for users who like to find related info from documents. It is powered by ***YandexGPTAPI***, Redis and ChromaDB + PostgresDB for logs.

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
   5.  `` pip install -e .``
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
  "query": "Tell me what do you know about worker union?",
  "user_id": "2",
  "request_id": "md5hash",
  "source_name": "test"
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
 - [X] QueryHelpManager (rewrite or modify user query in case of problems with query)
 - [ ] QueryFilterManager (check that user query are not just a SPAM)
 - [x] Docker Image
 - [X] Docker-Compose for test and prod.
 - [X] Nginx to control interactions.
 - [X] github workflow for CI
 - [X] README setup locally .
 - [X] Async libraries to interact with users instead of telegrambotapi. -> case for telegram on desktop.
 - [X] Add options to use manual prompt files. -> ./prompts
-  [X] Fix Reranker logic. -> bm25 over selected text
-  [X] CD logic to save images at docker registery server. -> github runner
-  [X] CD logic to deploy new image for chatbot on remote server. -> github runner
-  [X] Limitation for users to call the API. -> Redis.
-  [X] Backlog logic for all user request throw API calls. -> PostgresDB.
-  [ ] Baseline checker for generated text over backlog info. First check format, second check special questions retrieval.

### Future:
-  [ ] Async connections to ChromaDB & Redis?? How to proxy this at Nginx?
-  [ ] InternetSearchManager (surfing internet if no data available)


#### How to configure PostgresDB for logs?

1. Look at POSTGRES_DSN var in env example. There you will find EXPOSED PORT, IP and password, login.
2. Log into PostgresDB container
```docker exec -it postgres_test psql -U test_user -d test_db```
3. CREATE TABLE at PostgresDB.
```commandline
CREATE TABLE chat_request_audit (
    audit_id        SERIAL PRIMARY KEY,
    time_in         VARCHAR(20) NOT NULL,
    time_out        VARCHAR(20),
    user_id         VARCHAR(128) NOT NULL,
    source_name     VARCHAR(64) NOT NULL,
    request_id      VARCHAR(256) NOT NULL,
    query_in        VARCHAR(500) NOT NULL,
    response_out    TEXT,
    status          VARCHAR(32),
    execution_time  NUMERIC(12,6)
);
```
4. Check that table exists.
```commandline
SELECT * FROM chat_request_audit ORDER BY audit_id DESC LIMIT 5;
```
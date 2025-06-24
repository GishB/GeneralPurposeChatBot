# Telegram Bot - UnionHelperBot

 This is a telegram bot which can interact with AI models via YandexCloud API.
 Baseline idea is to help workers find related info from documents. It is powered by ***YandexGPTAPI***.

tg link:
> https://t.me/HelperUnionBot
 
 - To start interact you need just to type /start or /начать.
 - If you want just to know something just start to type and you easily find out your answer.

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

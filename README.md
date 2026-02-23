# Union Agents

 This is a repo to develop Union Agents.
 
General idea is to create chatbot which can interact with AI models via YandexCloud API.
 Baseline idea is to help developers run agent. It is powered by ***YandexGPTAPI***, Redis, ChromaDB and Langfuse.

If you would like to check this bot go to tg link (sometimes i will run this for tests):
> https://t.me/HelperUnionBot
 
 - To start interact you need just to type /start or /начать.
 - If you want just to know something just start to type and you easily find out your answer.

# UNDER CONSTRUCTION

## How to start?
0. Setup buildx for multiplatform building
```bash
docker buildx create --use --name multiarch
```
1. Build Docker image (works for ubuntu and mac):
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t unionchatbot:latest \
  -f mlops/docker/Dockerfile \
  --load .
```
2. Run the image:
```bash
docker run -p 8080:8000 --env-file .env.prod --name unionchatbot unionchatbot:latest
```
### Errors:
In case of image error you can do the following:
```bash
docker stop unionchatbot 2>/dev/null || true
docker rm unionchatbot 2>/dev/null || true
```
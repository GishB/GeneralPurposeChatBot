# UnionChatBot

![Tests](https://img.shields.io/badge/tests-102%2F102-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-79%25-green)
![Python](https://img.shields.io/badge/python-3.12-blue.svg?logo=python&logoColor=white)

`UnionChatBot` - REST-сервис с агентом на базе LangChain/LangGraph и YandexGPT API.
Проект включает:
- FastAPI API слой;
- граф агента с RAG-обогащением;
- Redis (semantic cache + rate limit);
- ChromaDB (векторный поиск);
- Postgres (чекпоинты состояния графа);
- Langfuse (трейсинг и промпты).

## Структура проекта

```text
.
├── src/
│   ├── service/                       # API, middleware, конфигурация, контекст приложения, логирование
│   │   ├── api/
│   │   │   ├── os_router.py           # /health, /info
│   │   │   ├── metric_router.py       # /like, /dislike
│   │   │   └── v1/
│   │   │       ├── router.py          # /api/v1/test_invoke, /api/v1/chat
│   │   │       ├── schemas.py         # Pydantic схемы запросов/ответов
│   │   │       └── utils.py           # обязательные service headers
│   │   ├── context.py                 # инициализация клиентов и зависимостей
│   │   └── config.py                  # настройки из env
│   ├── agents/
│   │   └── profkom_consultant/        # логика агентного графа
│   │       ├── nodes/                 # validate/decompose/answer/loop
│   │       ├── workflow/base.py       # сборка StateGraph
│   │       └── states/                # состояние и статусы агента
│   └── modules/
│       ├── chroma_ext/                # адаптер Chroma + embeddings + rerank + sync-скрипты
│       ├── redis_ext/                 # semantic cache и rate limiter
│       ├── postgres_ext/              # async pool и checkpointer для LangGraph
│       └── langfuse_ext/              # клиент и callback Langfuse
├── experiments/                       # ноутбуки, nginx-конфиги, скрипты загрузки данных
├── mlops/docker/                      # Dockerfile и compose-файлы для VM/production/swarm
├── .env.example                       # пример env для локальной разработки (с export)
├── .env.prod.example                  # пример env для docker/prod (KEY=VALUE)
└── pyproject.toml                     # зависимости и метаданные проекта
```

## Модули и их назначение

### 1) `src/service`
- Точка входа сервиса (`src/service/__main__.py`) и инициализация FastAPI.
- Роутинг, middleware логирования и служебные ручки.
- Централизованная конфигурация из переменных окружения (`APP_CONFIG`).
- Контейнер зависимостей (`APP_CTX`) и lifecycle (`on_startup`/`on_shutdown`).
- Логирование, метрики и аудит через `loguru`.

### 2) `src/agents/profkom_consultant`
- Реализация агента `UnionAgent`.
- Ноды графа:
  - валидация запроса/ответа;
  - декомпозиция вопроса;
  - генерация ответов по частям;
  - сборка финального ответа;
  - цикл "подумай еще раз", если ответ неполный.
- Сборка `StateGraph` в `workflow/base.py`.

### 3) `src/modules/chroma_ext`
- HTTP-адаптер к ChromaDB.
- Поиск релевантных документов, фильтрация по distance, BM25 rerank.
- Кастомный эмбеддер для Yandex embeddings API.
- Скрипты для синхронизации `.docx` в коллекцию Chroma.

### 4) `src/modules/redis_ext`
- Semantic cache для ответов/этапов агента.
- Ограничение частоты запросов пользователя (`UserRateLimiter`).

### 5) `src/modules/postgres_ext`
- Асинхронный connection pool.
- Чекпоинтер `AsyncPostgresSaver` для хранения состояния графа по пользователю.

### 6) `src/modules/langfuse_ext`
- Инициализация клиента Langfuse.
- Callback handler для трейсинга вызовов LLM и работы графа.

### 7) `experiments`
- Ноутбуки и прототипы по Yandex API, LangChain, Langfuse и логике агента.
- Примеры локального nginx + self-signed сертификатов.
- Утилиты подготовки и загрузки данных в Chroma.

### 8) `mlops/docker`
- `Dockerfile` для сборки сервиса.
- `docker-compose.yml` - базовый compose.
- `docker-compose-prod.yml` - вариант для VM с nginx и внешними volume.
- `docker-compose-swarm-prod.yml` - пример для Docker Swarm.

## Требования

- Python `3.12`
- `uv` для управления окружением
- Docker + Docker Buildx (для мультиплатформенной сборки)
- Доступные внешние сервисы: Redis, ChromaDB, Postgres, Langfuse (или их контейнерные аналоги)

## Конфигурация окружения

1. Для локальной разработки используйте шаблон:
```bash
cp .env.example .env
```

2. Для Docker/VM используйте шаблон:
```bash
cp .env.prod.example .env.prod
```

3. Заполните секреты и адреса сервисов в скопированном файле.

## Локальный запуск (без Docker)

```bash
uv sync --frozen --no-dev
uv run python src/service/__main__.py
```

После старта API доступно по адресу:
- `http://localhost:8080/health`
- `http://localhost:8080/docs`

## Типовой сценарий работы с `/chat` через `curl`

Фактический endpoint сервиса: `POST /api/v1/chat`.
Если nginx проксирует маршрут `/chat` в приложение, используйте URL `https://localhost/chat`.
Для nginx обязателен токен `X-API-TOKEN` (значение из `NGINX_TOKEN`), иначе nginx вернет `422`.

Обязательные заголовки:
- `x-trace-id`
- `x-request-time`
- `x-source-name`
- `x-user-id`
- `X-API-TOKEN` (только для запроса через nginx `/chat`)

Тело запроса:
```json
{
  "text": "Как вступить в профсоюз?",
  "organisation": "ППО Невинномысский Азот"
}
```

### Вариант 1. HTTPS localhost без проверки сертификата (`-k`)

```bash
curl -k --request POST "https://localhost/api/v1/chat" \
  --header "Content-Type: application/json" \
  --header "x-trace-id: $(uuidgen)" \
  --header "x-request-time: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --header "x-source-name: local-dev" \
  --header "x-user-id: user-001" \
  --data '{
    "text": "Как вступить в профсоюз?",
    "organisation": "ППО Невинномысский Азот"
  }'
```

Пример для проксированного endpoint `/chat`:

```bash
curl -k --request POST "https://localhost/chat" \
  --header "Content-Type: application/json" \
  --header "X-API-TOKEN: ${NGINX_TOKEN}" \
  --header "x-trace-id: $(uuidgen)" \
  --header "x-request-time: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --header "x-source-name: local-dev" \
  --header "x-user-id: user-001" \
  --data '{
    "text": "Как вступить в профсоюз?",
    "organisation": "ППО Невинномысский Азот"
  }'
```

### Вариант 2. Прямой вызов FastAPI без TLS

```bash
curl --request POST "http://localhost:8080/api/v1/chat" \
  --header "Content-Type: application/json" \
  --header "x-trace-id: $(uuidgen)" \
  --header "x-request-time: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --header "x-source-name: local-dev" \
  --header "x-user-id: user-001" \
  --data '{
    "text": "Как вступить в профсоюз?",
    "organisation": "ППО Невинномысский Азот"
  }'
```

## Типовой сценарий сборки Docker-образа (macOS / Ubuntu 22.04)

1. Один раз создайте buildx builder:
```bash
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap
```

2. Сборка локального образа под текущую платформу:
```bash
docker buildx build \
  --platform linux/amd64 \
  -t union-chatbot:latest \
  -f mlops/docker/Dockerfile \
  --load .
```

3. Сборка мультиплатформенного образа (amd64 + arm64) с публикацией в registry:
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t <registry>/union-chatbot:latest \
  -f mlops/docker/Dockerfile \
  --push .
```

Примечание:
- для Apple Silicon обычно целевая платформа `linux/arm64`;
- для большинства VM/серверов - `linux/amd64`.

## Типовой деплой Docker-образа на ВМ

Вариант через compose-файл из проекта (`mlops/docker/docker-compose-prod.yml`):

```bash
scp .env.prod user@vm:/opt/unionchatbot/.env.prod
scp mlops/docker/docker-compose-prod.yml user@vm:/opt/unionchatbot/docker-compose-prod.yml
ssh user@vm "cd /opt/unionchatbot && docker compose -f docker-compose-prod.yml pull"
ssh user@vm "cd /opt/unionchatbot && docker compose -f docker-compose-prod.yml up -d"
```

Для этого варианта на VM должны существовать nginx-конфиги, сертификаты и token-файлы в путях,
которые смонтированы в `docker-compose-prod.yml`.

## Типовой деплой локально

Локальный сценарий через `docker-compose.yml` с чтением секретов из `.env.prod`:

1. Подготовьте `.env.prod` и проверьте значения:
```bash
cp .env.prod.example .env.prod
```

Обязательно: `APP_HOST=0.0.0.0`, `APP_PORT=32000`, `PG_HOST=postgres_test`, `REDIS_HOST=redis`, `CHROMA_HOST=chromadb`.

2. Положите секреты в путь, который ожидает compose:
```bash
mkdir -p /opt/unionchatbot
cp .env.prod /opt/unionchatbot/.env.prod
```

3. Соберите образ и поднимите стек:
```bash
docker build -t union-chatbot:latest -f mlops/docker/Dockerfile .
docker compose -f mlops/docker/docker-compose.yml up -d
```

4. Проверка:
```bash
docker compose -f mlops/docker/docker-compose.yml exec chatbot curl -s http://127.0.0.1:32000/health
```

Остановка:
```bash
docker compose -f mlops/docker/docker-compose.yml down
```

Если нужен запуск через HTTPS и `/chat`, добавьте nginx как reverse-proxy с конфигами из `experiments/nginx`.

## Полезные материалы в репозитории

- `experiments/yandex_api` - эксперименты с YandexGPT API.
- `experiments/langchain_tests` - тестовые ноутбуки по LangChain.
- `experiments/langfuse_experiments` - эксперименты по трейсингу и промптам.
- `experiments/nginx` - примеры nginx-конфигурации и self-signed сертификатов.
- `experiments/scripts` - утилиты подготовки/загрузки данных.

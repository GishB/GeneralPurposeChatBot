# Используем Ubuntu вместо Debian
FROM --platform=linux/amd64 ubuntu:22.04 as builder

# Устанавливаем Python и системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Копируем только необходимые для установки файлы
COPY . .

# Создаем venv
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем зависимости через pip
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

# Финальный образ на основе Ubuntu
FROM --platform=linux/amd64 ubuntu:22.04

# Устанавливаем только Python без dev-зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    && rm -rf /var/lib/apt/lists/*

# Создаем непривилегированного пользователя
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /bin/bash appuser && \
    mkdir -p /app /opt/venv && \
    chown -R appuser:appuser /app /opt/venv

WORKDIR /app

# Копируем venv из builder-этапа
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем только необходимые файлы приложения
COPY --chown=appuser:appuser src/container_service/main.py .
COPY --chown=appuser:appuser src/UnionChatBot/prompts/WorkerUnionDefault.txt .
COPY --chown=appuser:appuser .env.example .

USER appuser

# Запуск через Gunicorn
CMD ["python3", "main.py"]
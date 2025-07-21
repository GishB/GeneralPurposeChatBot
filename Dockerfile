FROM --platform=linux/amd64 ubuntu:22.04 as builder

# Устанавливаем Python и системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    gcc \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Копируем только необходимые для установки файлы
COPY . .

# Создаем venv
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем зависимости через pip
RUN pip install --no-cache-dir -r requirements.prod.txt && \
    pip install --no-cache-dir .

# Загружаем необходимые данные NLTK в доступную папку
RUN mkdir -p /nltk_data && \
    chmod 777 /nltk_data && \
    /opt/venv/bin/python -m nltk.downloader -d /nltk_data punkt_tab

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
    mkdir -p /app /opt/venv /nltk_data && \
    chown -R appuser:appuser /app /opt/venv /nltk_data

WORKDIR /app

# Копируем venv из builder-этапа
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
# Копируем данные NLTK
COPY --from=builder --chown=appuser:appuser /nltk_data /nltk_data
ENV PATH="/opt/venv/bin:$PATH"
ENV NLTK_DATA="/nltk_data"

# Копируем только необходимые файлы приложения
COPY --chown=appuser:appuser src/container_service/main.py .
COPY --chown=appuser:appuser prompts/ ./prompts/.
COPY --chown=appuser:appuser README.md README.md
COPY --chown=appuser:appuser .env.example .env.example

USER appuser

# Запуск через main.py uvicorn __name__
CMD ["python3", "main.py"]
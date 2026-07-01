# syntax=docker/dockerfile:1.7

################################################################################
# Builder — компилятор и uv живут только здесь, в финальный образ не попадают
################################################################################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ROOT=/opt/app-root \
    HOME=/opt/app-root \
    UV_HOME=/opt/app-root/uv \
    UV_VENV=/opt/app-root/.venv \
    UV_LINK_MODE=copy

# Тулчейн для сборки нативных колёс (psycopg и т.п.) + uv
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev ca-certificates curl && \
    pip install --no-cache-dir uv && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app-root

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv venv --seed --python 3.12 "$UV_VENV"
ENV PATH="$UV_VENV/bin:$PATH"

# Только рантайм-зависимости (dev-группа с jupyter/ipython/scikit-learn исключена)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-python-downloads --no-dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv build && "$UV_VENV/bin/pip" install --no-cache-dir dist/*.whl

################################################################################
# Final — чистый slim, только рантайм: venv + src + libpq5, без компилятора/uv/pip-кэша
################################################################################
FROM python:3.12-slim AS final

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    APP_ROOT=/opt/app-root \
    HOME=/opt/app-root \
    PYTHONFAULTHANDLER=1 \
    PYTHONIOENCODING=UTF-8 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/app-root/.venv/bin:$PATH"

# Только рантайм-библиотека для psycopg + непривилегированный пользователь.
# Каталог приложения отдаём 1001: сервис по умолчанию пишет логи (app.log,
# app-metric.log, events.log) в свою рабочую директорию.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -d /opt/app-root -s /usr/sbin/nologin appuser && \
    mkdir -p /opt/app-root && chown 1001:1001 /opt/app-root

WORKDIR /opt/app-root

COPY --from=builder --chown=1001:1001 /opt/app-root/.venv /opt/app-root/.venv
COPY --from=builder --chown=1001:1001 /opt/app-root/src  /opt/app-root/src

USER 1001
ENTRYPOINT ["python3", "src/service/__main__.py"]

FROM python:3.12-slim AS base

USER root

ENV LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    APP_ROOT=/opt/app-root \
    HOME=/opt/app-root \
    PYTHONFAULTHANDLER=1 \
    PYTHONIOENCODING=UTF-8 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    UV_HOME=/opt/app-root/uv \
    UV_VENV=/opt/app-root/.venv

# Устанавливаем системные пакеты и uv через pip
RUN apt-get update && apt-get install -y curl ca-certificates build-essential libpq-dev && \
    pip install --no-cache-dir uv && \
    rm -rf /var/lib/apt/lists/*


################################################################################
# Builder
################################################################################
FROM base AS builder

USER root
WORKDIR /opt/app-root

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Используем uv напрямую (он уже в PATH)
RUN uv venv --seed --python 3.12 "$UV_VENV"
ENV PATH="$UV_VENV/bin:$PATH"
RUN uv sync --frozen --no-python-downloads --no-dev

RUN uv build && $UV_VENV/bin/pip install dist/*.whl

################################################################################
# Final
################################################################################
FROM base AS final

USER root
WORKDIR /opt/app-root

COPY --from=builder /opt/app-root/.venv /opt/app-root/.venv
COPY --from=builder /opt/app-root/src /opt/app-root/src

ENV PATH="/opt/app-root/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -d /opt/app-root -s /bin/bash appuser && \
    chown -R 1001:1001 /opt/app-root

USER 1001
ENTRYPOINT ["python3", "src/service/__main__.py"]
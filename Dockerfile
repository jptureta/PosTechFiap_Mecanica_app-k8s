FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev python3-dev libc6-dev && \
    rm -rf /var/lib/apt/lists/*

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Camada de dependências (cache friendly): muda só se pyproject/uv.lock mudarem
COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev --no-install-project; \
    else \
        uv sync --no-dev --no-install-project; \
    fi

# Código da aplicação + instalação do projeto no venv
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY README.md ./
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev; \
    else \
        uv sync --no-dev; \
    fi

FROM python:3.12-slim AS runtime

ARG APP_USER=appuser
ARG APP_UID=1000

# libpq5 = runtime do psycopg2; curl para HEALTHCHECK
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r ${APP_USER} && \
    useradd -r -g ${APP_USER} -u ${APP_UID} -m ${APP_USER}

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Copia venv pronto e código-fonte com ownership correto
COPY --from=builder --chown=${APP_USER}:${APP_USER} /opt/venv /opt/venv
COPY --chown=${APP_USER}:${APP_USER} app/ ./app/
COPY --chown=${APP_USER}:${APP_USER} alembic/ ./alembic/
COPY --chown=${APP_USER}:${APP_USER} alembic.ini ./

USER ${APP_USER}

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/ || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

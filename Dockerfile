FROM node:22-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY pipeline/ pipeline/
COPY server/ server/
COPY --from=web /web/dist web/dist
ENV DATA_DIR=/app/data
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]

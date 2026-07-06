FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY Source/ ./Source/

EXPOSE 8003

CMD ["uv", "run", "uvicorn", "Source.app.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]

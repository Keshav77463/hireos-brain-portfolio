FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/workspace/.venv/bin:$PATH"

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-cache
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY tests ./tests
COPY fixtures ./fixtures
COPY alembic.ini ./
RUN groupadd --gid 10001 hireos && useradd --uid 10001 --gid hireos --no-create-home hireos
USER hireos
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

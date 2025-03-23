FROM python:3.12-alpine AS builder
ENV UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --compile-bytecode --no-install-project

FROM python:3.12-alpine
EXPOSE 8000
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY --from=builder /app /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --compile-bytecode
CMD ["uv", "run", "src/main.py"]
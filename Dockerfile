FROM alpine:3.21
EXPOSE 8000
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . /app
WORKDIR /app
RUN apk add --no-cache python3~=3.12&& \
    uv sync --frozen --compile-bytecode
CMD ["uv", "run", "src/main.py"]
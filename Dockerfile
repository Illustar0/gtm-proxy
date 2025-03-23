FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
EXPOSE 8000
COPY . /app
WORKDIR /app
RUN uv sync --frozen --compile-bytecode
CMD ["uv", "run", "src/main.py"]
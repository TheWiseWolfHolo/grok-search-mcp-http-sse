FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install project dependencies from pyproject.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

EXPOSE 8000

# Recommended defaults for remote MCP deployment.
ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_PATH=/mcp \
    MCP_SSE_PATH=/sse \
    MCP_MESSAGE_PATH=/messages/ \
    FASTMCP_SHOW_SERVER_BANNER=false \
    FASTMCP_ENABLE_RICH_LOGGING=false \
    FASTMCP_LOG_LEVEL=ERROR \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8

CMD ["python", "-m", "grok_search.server"]


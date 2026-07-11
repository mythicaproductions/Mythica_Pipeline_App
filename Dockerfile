# MCP server image (Railway / Fly.io). Desktop app is not part of this image.
FROM python:3.12-slim

WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# PORT is provided by the host at runtime; default 8000 for local docker run.
CMD ["sh", "-c", "uvicorn mcp_server:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]

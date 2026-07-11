# MCP server image (Railway / Fly.io). Desktop app is not part of this image.
FROM python:3.12-slim

WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Start via Python so it reads $PORT itself (os.environ) — avoids relying on
# shell variable expansion, which some hosts skip (passing a literal "$PORT").
CMD ["python", "src/mcp_server.py"]

# Imagen del servidor MCP de IT — VERSIÓN VULNERABLE.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/
COPY servers/it/ ./servers/it/

WORKDIR /app/servers/it

ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=9003
EXPOSE 9003

CMD ["python", "server.py"]

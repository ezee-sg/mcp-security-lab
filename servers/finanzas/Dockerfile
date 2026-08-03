# Imagen del servidor MCP de Finanzas — VERSIÓN VULNERABLE.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/
COPY servers/finanzas/ ./servers/finanzas/

WORKDIR /app/servers/finanzas

ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=9002
EXPOSE 9002

CMD ["python", "server.py"]

# Imagen del servidor MCP de RRHH — VERSIÓN VULNERABLE.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/
COPY servers/rrhh/ ./servers/rrhh/

WORKDIR /app/servers/rrhh

ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=9001
EXPOSE 9001

CMD ["python", "server.py"]

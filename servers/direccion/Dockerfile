# Imagen del servidor MCP de Dirección — VERSIÓN VULNERABLE.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/
COPY servers/direccion/ ./servers/direccion/

WORKDIR /app/servers/direccion

ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=9004
EXPOSE 9004

CMD ["python", "server.py"]

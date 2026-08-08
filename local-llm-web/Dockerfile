FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY local-llm-web/ ./local-llm-web/

WORKDIR /app/local-llm-web
EXPOSE 8000
CMD ["python", "app.py"]

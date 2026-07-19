FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY monitoring/ ./monitoring/
COPY prompts/ ./prompts/
COPY scripts/ ./scripts/
COPY evaluation/ ./evaluation/

RUN python scripts/seed_data.py

EXPOSE 8000 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

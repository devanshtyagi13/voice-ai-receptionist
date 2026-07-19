FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything preserving folder structure
COPY backend/ ./backend/
COPY monitoring/ ./monitoring/
COPY prompts/ ./prompts/
COPY scripts/ ./scripts/
COPY evaluation/ ./evaluation/

# Seed the database at build time
ENV PYTHONPATH=/app/backend
ENV DATABASE_URL=sqlite:////app/clinic.db
RUN python scripts/seed_data.py

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

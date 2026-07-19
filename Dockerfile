FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full folder structure
COPY backend/ ./backend/
COPY monitoring/ ./monitoring/
COPY prompts/ ./prompts/
COPY scripts/ ./scripts/
COPY evaluation/ ./evaluation/

# Set PYTHONPATH so all imports resolve correctly
ENV PYTHONPATH=/app/backend
ENV DATABASE_URL=sqlite:////app/clinic.db

# Seed database at build time
RUN python scripts/seed_data.py

EXPOSE 8000

# Use shell form so env vars are expanded properly
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

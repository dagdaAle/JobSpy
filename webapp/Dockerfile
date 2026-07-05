FROM python:3.11-slim

# Avoid interactive prompts, keep Python output unbuffered for logs.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FEEDBACK_DB=/data/feedback.db

WORKDIR /app

# 1) Install web dependencies first (better layer caching).
COPY webapp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 2) Copy the JobSpy library and install it (no deps: already in requirements).
COPY pyproject.toml /src/pyproject.toml
COPY README.md /src/README.md
COPY jobspy /src/jobspy
RUN pip install --no-cache-dir --no-deps /src

# 3) Copy the web app itself.
COPY webapp/app.py /app/app.py
COPY webapp/storage.py /app/storage.py
COPY webapp/analyzer.py /app/analyzer.py
COPY webapp/static /app/static

# Feedback DB lives here (mounted as a volume in docker-compose).
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

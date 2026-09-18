FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app main.py .

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--no-server-header"]

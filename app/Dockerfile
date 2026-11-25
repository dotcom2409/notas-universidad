# Imagen oficial y liviana
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PORT=8000

WORKDIR /app

# Usuario sin privilegios (no root) para ejecutar la app
RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"APP_PORT\",\"8000\")}/health', timeout=4)" || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${APP_PORT} --proxy-headers --forwarded-allow-ips='*'"]

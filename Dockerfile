FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ATLAS_WEB_MODE=cloud \
    ATLAS_AUTH_MODE=google_oauth \
    ATLAS_DATA_ROOT=/tmp/atlas-data \
    PORT=8080

WORKDIR /app

COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

COPY app ./app
COPY web ./web
COPY data/security_universe.json ./data/security_universe.json
COPY cloud_dashboard.py cloud_daily.py cloud_sync.py cloud_weekly.py ./
COPY main.py weekly_summary.py ./

RUN useradd --create-home --uid 10001 atlas
USER atlas

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"

CMD ["python", "cloud_dashboard.py"]

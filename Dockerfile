FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    TENDERPROOF_ALLOW_PAID_API=0 \
    TENDERPROOF_RUNTIME_DIR=/data \
    TENDERPROOF_DEMO_DIR=/demo \
    TMPDIR=/data

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY web/requirements.txt ./web/requirements.txt

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir -r web/requirements.txt \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app /home/app

COPY --chown=app:app *.py ./
COPY --chown=app:app web/api.py web/app.py web/ui.css ./web/
COPY --chown=app:app .streamlit/config.toml ./.streamlit/config.toml

USER 10001:10001

EXPOSE 8000 8501

CMD ["python", "-m", "uvicorn", "web.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
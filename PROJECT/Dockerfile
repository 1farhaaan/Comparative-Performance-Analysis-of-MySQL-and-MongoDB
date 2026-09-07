FROM python:3.14.2-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn pymysql

COPY . .

# Delete ALL Python bytecode cache — prevents stale .pyc files
# from old builds causing mapper configuration errors
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
RUN find /app -name "*.pyc" -delete 2>/dev/null || true

ENV FLASK_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONNOPYCACHE=1

EXPOSE 5000

CMD ["gunicorn", "wsgi:app", "--workers", "3", "--bind", "0.0.0.0:5000", "--timeout", "120"]
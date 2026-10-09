FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py bootstrap_openobserve || true; python manage.py observability_heartbeat --interval 30 & python manage.py export_waf_audit --path /var/log/waf/audit/audit.json & exec python manage.py runserver 0.0.0.0:8000"]

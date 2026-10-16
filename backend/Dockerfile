FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 이미지 생성 단계에서 정적 파일을 모아 실행 시 파일 생성과 권한 문제를 피합니다.
RUN DJANGO_DEBUG=true python manage.py collectstatic --noinput

# 컨테이너가 root 권한으로 웹 요청을 처리하지 않도록 전용 계정을 사용합니다.
RUN addgroup --system django \
    && adduser --system --ingroup django django \
    && mkdir -p /data /app/media \
    && chown -R django:django /app
RUN chown -R django:django /data

USER django

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]

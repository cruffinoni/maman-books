FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data && \
    adduser --disabled-password --gecos "" botuser && \
    chown botuser /app/data

USER botuser

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

CMD ["python", "bot.py"]

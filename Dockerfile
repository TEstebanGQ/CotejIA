FROM python:3.12-slim

# opencv (dependencia de rapidocr) necesita libGL y glib en tiempo de ejecución
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
EXPOSE 8000

# Por defecto levanta API + dashboard; para el harness:
#   docker compose run --rm app python main.py audit --dir /casos
CMD ["python", "main.py", "web", "--host", "0.0.0.0", "--port", "8000"]

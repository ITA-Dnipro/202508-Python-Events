FROM python:3.10-slim 

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc postgresql-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONPATH /app

EXPOSE 8006

CMD ["uvicorn", "events_app.main:app", "--host", "0.0.0.0", "--port", "8006"]
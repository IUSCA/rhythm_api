FROM python:3.11.2

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True
WORKDIR /app

RUN pip install -U pip poetry==1.4
COPY ./poetry.lock ./pyproject.toml ./
RUN poetry export --without-hashes --format=requirements.txt > requirements.txt
RUN pip install -r requirements.txt

# .dockerignore prevents all files to be copied
# instead only .env and rhythm_api directory will be copied
COPY . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 1 --timeout 0 rhythm_api.app:app
# HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 CMD curl -f http://localhost:$PORT/health

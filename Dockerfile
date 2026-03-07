FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY bot/ bot/
COPY assets/ assets/

CMD ["python", "-m", "bot"]

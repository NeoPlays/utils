FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir flask gunicorn requests

EXPOSE 8080

CMD ["python", "main.py"]

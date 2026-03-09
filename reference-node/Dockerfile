FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY reference-node/requirements.txt /app/reference-node/requirements.txt
RUN pip install --no-cache-dir -r /app/reference-node/requirements.txt

COPY . /app

EXPOSE 8080

CMD ["python3", "reference-node/server.py", "--host", "0.0.0.0", "--port", "8080", "--manifest", "/app/manifest.json", "--schemas-dir", "/app/schemas", "--tools-out-dir", "/app/tools/out", "--capabilities-file", "/app/reference-node/capabilities.local.json"]

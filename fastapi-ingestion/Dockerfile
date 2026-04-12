FROM python:3.12-slim

WORKDIR /app

# Copy shared package outside /app so volume mounts cannot shadow it
COPY shared/ /packages/shared/
ENV PYTHONPATH=/packages

COPY fastapi-ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fastapi-ingestion/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--loop", "uvloop", "--workers", "4"]

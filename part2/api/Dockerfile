FROM python:3.12-slim

WORKDIR /app

COPY pipeline/requirements.txt /tmp/pipeline-req.txt
RUN pip install --no-cache-dir -r /tmp/pipeline-req.txt

COPY api/requirements.txt /tmp/api-req.txt
RUN pip install --no-cache-dir -r /tmp/api-req.txt

COPY pipeline /app/pipeline
COPY api /app/api

ENV PYTHONPATH=/app/pipeline:/app
ENV DATASET_ROOT=/data
ENV OUT_DIR=/data/out
ENV INCOMING_DIR=/data/incoming
ENV PDF_BATCH_DIR=/data/pdfs
ENV PIPELINE_ROOT=/app/pipeline

EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]

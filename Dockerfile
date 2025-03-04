FROM python:3.9-alpine

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY DATA_MAIN/ ./DATA_MAIN/

# Set environment variables
ENV FLASK_APP=src.api
ENV PYTHONPATH=/app

# Expose the port
EXPOSE 8080

# Run with Gunicorn - single worker/thread for serverless
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "2", "src.api:app"]
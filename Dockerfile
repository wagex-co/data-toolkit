FROM python:3.9-alpine

WORKDIR /app

# Install Chrome and ChromeDriver dependencies
RUN apk add --no-cache \
    chromium \
    chromium-chromedriver \
    # Required dependencies for Chrome
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    # Build dependencies
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo

# Set Chrome environment variables
ENV CHROME_BIN=/usr/bin/chromium-browser \
    CHROME_PATH=/usr/lib/chromium/ \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

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
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies if required
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Make start script executable
RUN chmod +x start.sh

# Run production entrypoint script (runs migrations and starts uvicorn on $PORT)
CMD ["./start.sh"]

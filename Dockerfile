FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make sure .env file is copied (optional, can use docker env instead)
# COPY .env .env

CMD ["uvicorn", "base.main:app", "--host", "0.0.0.0", "--port", "8000"]
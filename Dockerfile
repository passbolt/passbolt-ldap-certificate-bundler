# Example Dockerfile for building an LDAPS Certificate Bundler container
# Minimal, reproducible environment
FROM python:3.11-slim

# Install system dependencies for cryptography and OpenSSL CLI
RUN apt-get update && apt-get install -y \
        build-essential libssl-dev libffi-dev python3-dev openssl \
                && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of project files
COPY . /app

# Default command (can be overridden)
ENTRYPOINT ["python", "ldaps_cert_chain_retriever.py"]

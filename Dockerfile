# Use Python slim image for smaller size while maintaining compatibility
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copy the entire app directory
COPY . .

# Create non-root user for security
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /var/www/programas/logs && \
    chown -R appuser:appuser /var/www/programas

# Switch to non-root user
USER appuser

# Set environment variables - make sure Python can find the modules in the app directory
ENV PYTHONPATH=/app \
    PATH="/usr/local/bin:$PATH" \
    FLASK_APP=app.wsgi:application \
    FLASK_ENV=production

# Expose the port
EXPOSE 8000

# Use gunicorn for production with optimal settings
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--worker-class", "gthread", "--worker-tmp-dir", "/dev/shm", "--timeout", "60", "app.wsgi:application"]
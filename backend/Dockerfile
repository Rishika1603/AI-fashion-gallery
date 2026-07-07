FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy lean deploy requirements (excludes heavy ML libs to stay under
# Railway free-plan resource caps; image search reports 503 gracefully)
COPY backend/requirements-deploy.txt ./requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy only the backend source code (keeps the image lean)
COPY backend/ ./backend/

# Create uploads directory
RUN mkdir -p backend/uploads

# Environment setup
ENV LOG_LEVEL=INFO
ENV HOST=0.0.0.0
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
# Disable the free Gradio HF Spaces try-on backend by default — its
# /heartbeat endpoint returns 404 on the upstream Space and floods
# logs. Set ENABLE_GRADIO_TRYON=1 to re-enable, or configure a paid
# backend (Fashn.ai, Replicate) to take its place.
ENV ENABLE_GRADIO_TRYON=0

# Expose the API port
EXPOSE 8000

# Start script handles $PORT via shell
RUN chmod +x /app/backend/start.sh
CMD ["/app/backend/start.sh"]

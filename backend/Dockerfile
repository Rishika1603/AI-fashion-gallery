FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy lean deploy requirements (excludes heavy ML libs to stay under
# Chat/search runtime deps + try-on
COPY backend/requirements-deploy.txt ./requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Backend source
COPY backend/ ./backend/

ENV LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONUNBUFFERED=1 \
    GRPC_VERBOSITY=NONE \
    ENABLE_GRADIO_TRYON=0 \
    ENABLE_AUTO_INGEST=0 \
    ALLOWED_ORIGINS=https://ai-fashion-gallery-frontend-production.up.railway.app,https://backend-production-a95c.up.railway.app

RUN mkdir -p backend/uploads

EXPOSE 8000

RUN chmod +x /app/backend/start.sh
CMD ["/app/backend/start.sh"]

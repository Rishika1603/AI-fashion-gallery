FROM python:3.11-slim

WORKDIR /app

# Every dependency below ships a manylinux wheel for cp311, so no compiler
# toolchain is needed. Skipping build-essential keeps the image well under
# Railway's size limit and cuts the build time substantially.
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
    ALLOWED_ORIGINS=https://ai-fashion-gallery-frontend-production.up.railway.app,https://ai-fashion-gallery-backend-production.up.railway.app

# Bake the product catalog into the image. The dataset is far too large to
# ship, so the catalog is rebuilt from the bundled Cloudinary URL mapping.
RUN python -m backend.seed_from_mapping

RUN mkdir -p backend/uploads

EXPOSE 8000

RUN chmod +x /app/backend/start.sh
CMD ["/app/backend/start.sh"]

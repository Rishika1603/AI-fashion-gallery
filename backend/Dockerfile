FROM python:3.11-slim

WORKDIR /app

# Every dependency below ships a manylinux wheel for cp311, so no compiler
# toolchain is needed. Skipping build-essential keeps the image well under
# Railway's size limit and cuts the build time substantially.
COPY backend/requirements-deploy.txt ./requirements-deploy.txt
COPY backend/requirements-deploy-ml.txt ./requirements-deploy-ml.txt
RUN pip install --no-cache-dir --prefer-binary -r requirements-deploy.txt

# The CLIP stack (torch + transformers) costs ~370 MB of RSS and ~610 MB of
# image, which does not fit a Railway Free/Trial service (0.5 GB RAM). It is
# therefore opt-in: set the build variable INSTALL_ML=1 on a plan with
# >= 2 GB RAM to enable "search by photo".
# Without it the app starts fine and /api/search-by-photo answers 503.
ARG INSTALL_ML=0
RUN if [ "$INSTALL_ML" = "1" ]; then \
      pip install --no-cache-dir --prefer-binary -r requirements-deploy-ml.txt; \
    else \
      echo "[build] INSTALL_ML=$INSTALL_ML — skipping torch/transformers"; \
    fi

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
# DATABASE_URL is cleared so this always writes the bundled SQLite catalog
# and never depends on a database being reachable at build time.
RUN DATABASE_URL= python -m backend.seed_from_mapping

RUN mkdir -p backend/uploads

EXPOSE 8000

RUN chmod +x /app/backend/start.sh
CMD ["/app/backend/start.sh"]

# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build with API base URL. For same-service nginx proxy, use /api (default).
# For separa...[truncated]

# Production stage - nginx
FROM nginx:alpine

# Copy built assets to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Replace default config with our own for SPA routing.
# Also proxy /api requests to the backend service (set RAILWAY_BACKEND_URL
# at deploy time, or hardcode the backend domain here for simplicity).
ARG RAILWAY_BACKEND_URL
ENV RAILWAY_BACKEND_URL=${RAILWAY_BACKEND_URL}

# Write nginx config with optional /api proxy if backend URL is set
RUN if [ -n "$RAILWAY_BACKEND_URL" ]; then \
      echo "server { \
        listen 80; \
        location /api/ { \
          proxy_pass ${RAILWAY_BACKEND_URL}/api/; \
          proxy_set_header Host \$host; \
          proxy_set_header X-Real-IP \$remote_addr; \
          proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for; \
          proxy_set_header X-Forwarded-Proto \$scheme; \
        } \
        location /static/ { \
          proxy_pass ${RAILWAY_BACKEND_URL}/static/; \
          proxy_set_header Host \$host; \
        } \
        location / { \
          root /usr/share/nginx/html; \
          index index.html index.htm; \
          try_files \$uri \$uri/ /index.html; \
        } \
      }" > /etc/nginx/conf.d/default.conf; \
    else \
      echo "server { \
        listen 80; \
        location / { \
          root /usr/share/nginx/html; \
          index index.html index.htm; \
          try_files \$uri \$uri/ /index.html; \
        } \
      }" > /etc/nginx/conf.d/default.conf; \
    fi

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

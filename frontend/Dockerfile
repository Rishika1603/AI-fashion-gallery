# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build with API base URL. Set as a build arg so it can be overridden
# at deploy time without editing the Dockerfile. Defaults to /api, which
# the nginx reverse proxy forwards to the backend (same-origin, no CORS).
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Production stage - nginx
FROM nginx:alpine

# Copy built assets to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Origin of the backend API, used by the /api reverse proxy. Override it
# with a Railway service variable named BACKEND_URL — the nginx entrypoint
# renders the template at container start, so no rebuild is needed.
ENV BACKEND_URL=https://ai-fashion-gallery-backend-production.up.railway.app

# Drop the stock config; the entrypoint renders our template instead.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

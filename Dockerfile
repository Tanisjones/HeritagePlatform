# Multi-stage Dockerfile for easier deployment
# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

# Stage 2: Build Backend & Serve
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gettext \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    proj-bin \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements /app/backend/requirements
RUN pip install --no-cache-dir -r /app/backend/requirements/production.txt

# Copy backend code
COPY backend /app/backend
WORKDIR /app/backend

# Copy built frontend assets to Django static and templates
# 1. Copy all build output (assets, favicon, etc) to static directory so collectstatic picks them up
COPY --from=frontend-builder /app/frontend/dist /app/backend/static/

# 2. Copy index.html to templates directory so it can be served by TemplateView
COPY --from=frontend-builder /app/frontend/dist/index.html /app/backend/templates/index.html

# Copy entrypoint script
COPY docker/backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

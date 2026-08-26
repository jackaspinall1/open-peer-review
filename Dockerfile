# Single image: builds the frontend, then serves it plus the API from one
# process. One container means no cross-origin cookie handling and one thing to
# deploy, which suits a tool that should cost a few pounds a month to run.
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /build/dist ./static
# DATA_DIR holds the SQLite database and uploaded PDFs; mount a volume here or
# every deploy loses the reviews.
ENV STATIC_DIR=/app/static DATA_DIR=/data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

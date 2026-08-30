# Stage 1: Build the React frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the Python backend and serve
FROM python:3.11-slim
WORKDIR /app/backend

# Install system dependencies (required for some Python packages like PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application
COPY backend/ ./

# Copy the built React app from the frontend-build stage
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Expose port
EXPOSE 8001

# Command to run the unified application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

# Stage 1: Build React Application
FROM node:20-alpine AS builder

WORKDIR /app

# Build arguments
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_API_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_URL=$VITE_API_URL

# Copy dependencies manifest
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code and config
COPY . .

# Build production bundle
RUN npm run build

# Stage 2: Serve production bundle with NGINX
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]

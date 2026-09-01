FROM node:22-alpine

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

CMD ["sh", "-c", "mkdir -p /app/result_build && cp -r dist/. /app/result_build/"]

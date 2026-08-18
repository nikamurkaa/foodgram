FROM node:21.7.1-alpine

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

CMD ["sh", "-c", "cp -r build /app/result_build/"]

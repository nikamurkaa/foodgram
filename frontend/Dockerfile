FROM node:22-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . ./
RUN npm run build

CMD ["sh", "-c", "mkdir -p result_build && cp -r dist/. result_build/"]

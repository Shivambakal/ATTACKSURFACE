FROM node:22-bookworm-slim
WORKDIR /app

ARG API_INTERNAL_URL=http://api:8000
ARG NEXT_PUBLIC_API_URL=""

ENV API_INTERNAL_URL=${API_INTERNAL_URL} \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    npm_config_audit=false \
    npm_config_fund=false \
    npm_config_fetch_retries=3 \
    npm_config_fetch_retry_mintimeout=1000 \
    npm_config_fetch_retry_maxtimeout=10000 \
    npm_config_fetch_timeout=60000

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]


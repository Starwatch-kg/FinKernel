FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --frozen-lockfile

COPY . .

ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── production image with nginx ──────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

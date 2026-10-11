# Pagedrill by Ouroboros. Node serves MCP, uploads, and downloads.
# Python formats the .docx. Do not deploy from this file unless asked.
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:22-bookworm-slim
WORKDIR /app
ENV NODE_ENV=production
ENV PAGEDRILL_HTTP_ONLY=1
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip \
  && pip3 install --break-system-packages 'python-docx>=1.1,<2' \
  && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist
COPY engine ./engine
COPY profiles ./profiles
USER node
EXPOSE 3000
CMD ["node", "dist/src/server.js"]

FROM node:22-slim

# Install Chromium and required fonts for Puppeteer / whatsapp-web.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

CMD ["sh", "-c", "rm -f /app/.wwebjs_auth/session/Singleton* /app/.wwebjs_auth/session/DevToolsActivePort 2>/dev/null || true; exec node index.js"]


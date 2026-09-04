FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
# Next.js resolves rewrites at build time; Docker Compose routes this hostname internally.
ENV METIS_API_URL=http://backend:8000
RUN npm run build
EXPOSE 3000
CMD ["node", ".next/standalone/server.js"]

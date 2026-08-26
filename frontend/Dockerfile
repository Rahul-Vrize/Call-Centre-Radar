FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Dev server: the dashboard is iterated on constantly during the build week,
# and `next dev` keeps hot reload working against the mounted source.
# For a production image, swap to: RUN npm run build && CMD ["npm", "start"]
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./

# `npm install`, not `npm ci`, on purpose.
#
# The lock file is generated on the developer's machine (Windows here), and npm
# records platform-specific OPTIONAL dependencies — the @emnapi/* native shims
# among them. Those differ on linux/amd64 inside this image, and `npm ci`
# treats any such divergence as a fatal "lock file out of sync" error rather
# than resolving it. `npm install` reconciles the platform bits while still
# honouring the locked versions for everything else, so the build works from a
# clean clone on any host OS.
RUN npm install --no-audit --no-fund

COPY . .

EXPOSE 3000

# Dev server: the dashboard is iterated on constantly, and `next dev` keeps hot
# reload working against the source mounted by docker-compose.
# For a production image, swap to: RUN npm run build && CMD ["npm", "start"]
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

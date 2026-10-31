# Stage 1: Node builds the app into plain files in dist/.
FROM node:24.22.1-alpine AS build
WORKDIR /app

# Packages first. Docker reuses this layer until the lock file changes,
# so a code change doesn't reinstall every package.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: only Nginx and the built files. Node and node_modules stay behind.
FROM nginx:1.30.6-alpine
# Security fixes Alpine published after this image was made (the T29 scan found
# curl and brotli). It stays on the same Alpine version: fixes only.
RUN apk upgrade --no-cache
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

# Run as Nginx's own normal user, not root (D27). It needs to write its
# process-id file and its temp files, so it gets those two places.
RUN touch /run/nginx.pid && chown nginx:nginx /run/nginx.pid && chown -R nginx:nginx /var/cache/nginx
USER nginx

EXPOSE 8080

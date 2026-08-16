# syntax=docker/dockerfile:1

FROM node:20-alpine AS build
WORKDIR /app
COPY packages/web-runtime /packages/web-runtime
COPY products/tracking/frontend/package.json ./
RUN npm install
COPY products/tracking/frontend ./
RUN npm run build

FROM nginx:alpine
COPY products/tracking/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY products/tracking/frontend/public/config.json /usr/share/nginx/html/config.json
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

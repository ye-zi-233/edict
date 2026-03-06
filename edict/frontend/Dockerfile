# ⚔️ Edict 三省六部 — 前端镜像
#
# 多阶段构建：Node 构建 React → Nginx 静态服务
# Nginx 反向代理 /api/ 和 /ws 到后端

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --silent
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]

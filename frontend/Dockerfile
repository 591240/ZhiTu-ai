# 知途 AI 旅行 —— 前端（Vue3 运营/自检面板）
# 多阶段构建：Node 仅用于打包，运行阶段只用 Nginx + 静态 dist，镜像体积小。

# ===== 阶段 1：构建 dist =====
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
# 国内镜像加速（阿里云 npm registry）
RUN npm config set registry https://registry.npmmirror.com \
    && npm install
COPY . .
# 限制 Node 堆内存，避免 2GB 服务器 OOM
RUN NODE_OPTIONS=--max-old-space-size=1024 npm run build

# ===== 阶段 2：运行 =====
FROM nginx:alpine
# 时区
ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone
# 静态产物
COPY --from=build /app/dist /usr/share/nginx/html
# 站点配置（静态托管 + /api 反代 backend）
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

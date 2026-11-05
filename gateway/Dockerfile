# 知途 AI 旅行 —— 网关镜像（纯 Nginx 反向代理）
# 用户端是微信小程序，由微信平台托管；本镜像只做 TLS 后端透传与 /api、/static 反代，
# 不含任何前端构建产物，因此没有 Node 构建阶段。
FROM nginx:alpine

ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

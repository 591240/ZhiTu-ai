# 知途 AI 旅行 —— 后端镜像
# 基于打包后的 Python 依赖 + 源码构建，内置阿里云 PyPI 镜像源。
# 适配 2 核 2GB 服务器：单 worker、受限内存。

FROM python:3.11-slim

# 时区与运行时依赖（curl 供健康检查使用）
ENV TZ=Asia/Shanghai \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata curl \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖层（利用构建缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷源码（注意：.env 已在 .dockerignore 排除，运行时由 Compose 注入环境变量）
COPY . .

EXPOSE 8000

# 2 核 2GB 下仅 1 个 worker；workers 可通过环境变量覆盖
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1}"]

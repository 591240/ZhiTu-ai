# 知途 AI 旅行 —— 向量库镜像（milvus-lite 引擎，对外是标准 Milvus gRPC 协议）
#
# 为什么不用官方 milvusdb/milvus 镜像：
#   Standalone 要连带拉起 etcd + MinIO 共 3 个容器、整机约 3 GB 起，
#   本部署目标是 2 vCPU / 2 GB 服务器，现有 mem_limit 已排到 1696 MB，塞不下。
# 为什么 milvus-lite 能当服务用：
#   3.x 起它是纯 Python 包（底层 faiss-cpu），自带 `python -m milvus_lite server`
#   的 gRPC 入口，实测 pymilvus 用 http://host:19530 直接连，
#   COSINE 分数与本地点积误差 1e-7，标量字段 filter 下推有效。
# 代价必须认清楚（都是实测数）：
#   1) 单进程引擎，8 路并发检索时 p50 从 28 ms 涨到 350 ms——写读并发会排队；
#   2) 官方自我定位是 local development and testing，不是集群级方案；
#   3) 数据目录带文件锁，同一个库不能被两个进程同时打开，
#      所以建索引的 build_kb.py 也必须通过 http:// 连它，不能直接开文件。
# 换成官方 Milvus 的口子已经留在 docker-compose.yml 的 milvus 服务里。

FROM python:3.11-slim

ENV TZ=Asia/Shanghai \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

# 只有服务端需要 faiss；后端镜像装 pymilvus 客户端就够了，两边不要混。
RUN pip install --no-cache-dir "pymilvus>=2.4" "milvus-lite>=3.0"

VOLUME /var/lib/milvus

EXPOSE 19530

CMD ["python", "-m", "milvus_lite", "server", \
     "--data-dir", "/var/lib/milvus", \
     "--host", "0.0.0.0", \
     "--port", "19530"]

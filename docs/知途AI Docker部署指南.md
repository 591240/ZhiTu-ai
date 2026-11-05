# 知途 AI 旅行 · Docker Compose 全栈部署指南

> 适用环境：腾讯云轻量应用服务器 **2 vCPU / 2 GB / 40 GB SSD / 3 Mbps（月流量 200 GB）/ Ubuntu Server 24.04 LTS / Docker 27.5.1**
> 本文档基于项目真实源码（FastAPI 后端 + MySQL + Redis）生成，并参照《Docker Compose 部署参考文档》的约束落地。

---

## 1. 部署架构与范围

| 服务 | 镜像 | 作用 | 对外暴露 |
| --- | --- | --- | --- |
| `mysql` | mysql:8.0 | 业务数据库 `zhisuibanyou` | 仅 `127.0.0.1:3307`（SSH 隧道用） |
| `redis` | redis:7-alpine | 缓存 / 限流 / 扩展能力 | 仅 Compose 内网 |
| `milvus` | 自构建（`milvus/Dockerfile`，python:3.11-slim + milvus-lite） | RAG 向量库：存 1024 维向量与 city/name/kind/text/meta 标量字段，对外是标准 Milvus gRPC 协议 | 仅 Compose 内网 `19530` |
| `backend` | 自构建（python:3.11-slim） | FastAPI 接口、AI 规划、OCR、问答 | 仅内网 `8000` |
| `gateway` | 自构建（`gateway/Dockerfile`，Nginx） | 反向代理 `/api/*`、`/static/*` → backend；`/nginx-health` 探活；`/api/chat/`、`/api/plan/` 单独配 SSE 不缓冲 | 仅 `127.0.0.1:8081` |

> **多项目共存说明**：当前服务器 `114.132.239.20` 已部署「高保真项目」并占用 `80`、`3306` 等常规端口，因此本方案将 gateway 映射到 `127.0.0.1:8081`、MySQL 映射到 `3307`，避免端口冲突。知途AI 的公网入口由**宿主机 Nginx**（80/443 + 已备案域名 + TLS）反代到 `127.0.0.1:8081`，容器本身不直接对公网。

> **关于「没有 Web 前端」**：本项目的唯一用户端是**微信小程序**（由微信平台托管，不进容器），仓库里没有 `frontend/` 目录，也不该有——早期文档里写的「Vue3 运营面板」并不存在，实际服务是 `gateway`（纯 Nginx 反代）。任何人来问"能不能在浏览器打开看看"，答案是不能：小程序没有 H5 端。

网络隔离：
- `backend_net`：`mysql` / `redis` / `milvus` / `backend` / `gateway` 互通，均不暴露公网。

持久化卷：`mysql_data`（数据库文件）、`redis_data`（AOF 数据）、`milvus_data`（向量集合，删了不丢业务数据，但要用 `build_kb.py` 重建）。

---

## 2. 资源规划（2 核 2 GB 关键约束）

| 服务 | mem_limit | mem_reservation | cpus | 说明 |
| --- | --- | --- | --- | --- |
| mysql | 704 m | 600 m | 1.0 | `innodb-buffer-pool-size=256M` 压内存；原 800m，为 milvus 让出封顶余量 |
| redis | 256 m | 160 m | 0.5 | `--maxmemory 200mb` 硬性淘汰 |
| milvus | 320 m | 192 m | 1.0 | 实测 RSS：空载 123 m、100 次检索后 147 m（393 条 / 1024 维） |
| backend | 512 m | 256 m | 1.0 | `UVICORN_WORKERS=1` 单进程；import 基线约 190 m（app.main 103 m + pymilvus 89 m） |
| gateway | 128 m | 64 m | 0.5 | Nginx 反代，极轻 |
| **合计上限** | **~1.92 GB** | **~1.27 GB** | **4.0** | 按实测 RSS 估实际占用约 1.1 GB（含 OS/dockerd 约 350 m），仍在 2 G 内 |

- mem_limit 是封顶不是占用。封顶合计刻意压在物理内存附近，是为了避免两个容器同时冲高时被 OOM killer 随机选中；上线后请用 `docker stats` 复核一轮。
- CPU 配额总和 4.0 > 2 核：靠 `cpus` 软限制避免单服务独占，非硬性隔离。
- milvus 镜像实测约 **769 MB**（faiss-cpu + pyarrow + grpcio 都打在里面，后端镜像不含这些）。40 GB SSD 无压力，但首次 `build --pull` 的下量要有预期。
- milvus 服务只 `expose` 19530、不发布宿主机端口，所以不会和同机其他项目的 Milvus 抢端口（这台开发机上就已经有一个 `sf-milvus` 在跑）。
- ⚠️ milvus-lite 是**单进程引擎**，实测 8 路并发检索 p50 会从 28 ms 涨到 350 ms（读写都会排队）。当前小程序体量下不是瓶颈，但并发上去之后这里先出问题，届时换官方 Milvus（需 4 GB 机器）。
- **强烈建议**在服务器上创建 1 GB swap，防止首次构建或峰值 OOM：
  ```bash
  sudo fallocate -l 1G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
  ```

带宽/流量适配（3 Mbps / 200 GB/月）：
- Nginx 开启 `gzip`；`client_max_body_size 20m` 限制上传。
- 后端图片/封面走外链（Unsplash 等），不占本机流量与磁盘。
- 数据库、Redis、后端端口均不暴露公网，无额外出流量。

---

## 3. 前置条件与准备

1. 一台已创建好的腾讯云轻量应用服务器（配置见上），并记录**公网 IP：`114.132.239.20`**。
2. 本地或 CI 能 `ssh` 登录服务器（建议普通运维用户并加入 `docker` 组）。
3. 服务器已安装 Docker 27.5.1 与 Docker Compose v2（见第 4 节校验）。
4. 项目源码已上传到服务器（见第 5 节）。

> 本项目**不依赖 RabbitMQ / Elasticsearch**，按参考文档原则未纳入，降低内存压力。

---

## 4. 服务器环境校验

```bash
# 1) 系统与资源
cat /etc/os-release | grep VERSION=
uname -m
nproc
free -h
df -h /
swapon --show        # 应能看到第 2 节创建的 1G swap

# 2) Docker 版本（目标：27.5.1 / Compose v2）
docker --version
docker compose version
docker info | head -n 20
```

若当前用户无 Docker 权限：
```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker ps
```

预期：`Docker version 27.5.1`、`Docker Compose version v2.x`、`nproc=2`、`free -h` 内存约 2 GB。

---

## 5. 目录结构与源码上传

### 5.1 服务器目录结构

源码上传到 `/opt/zhitu-ai/`，结构如下（与仓库一致）：

```text
/opt/zhitu-ai/
├── docker-compose.yml
├── .env                      # 由 .env.example 复制并填写（chmod 600）
├── .env.example
├── server/                   # 后端（compose 的 build context: ./server）
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt      # 含 pymilvus（只是客户端，不含服务端依赖）
│   ├── requirements-dev.txt  # 含 milvus-lite，只本地/CI 用，不进镜像
│   ├── app/  kb/  scripts/  tests/
│   └── ...
├── gateway/                  # Nginx 反代（build context: ./gateway）
│   ├── Dockerfile
│   └── nginx.conf
└── milvus/                   # 向量库镜像（build context: ./milvus）
    └── Dockerfile            # 只有 Dockerfile，pip 装 milvus-lite + pymilvus
```

> 三个构建目录都要传上去，缺 `milvus/` 会让 `docker compose build` 直接失败。
> 仓库里没有 `frontend/`——它在 e27af7f 就删了，唯一用户端是微信小程序，不进容器。

### 5.2 上传方式（任选其一）

**方式 A：Git 克隆（推荐，便于后续更新）**
```bash
sudo mkdir -p /opt && sudo chown "$USER":"$USER" /opt
git clone <你的仓库地址> /opt/zhitu-ai
cd /opt/zhitu-ai
```

**方式 B：本地打包上传（无 Git 时）**
```bash
# 在本机项目根目录打包（排除本地无关文件）
tar --exclude='server/venv' --exclude='server/.venv' --exclude='server/__pycache__' \
    --exclude='miniprogram' --exclude='.git' --exclude='outputs' --exclude='ppt-defence' \
    -czf zhitu-ai.tar.gz docker-compose.yml .env.example server gateway milvus
# 上传到服务器
scp zhitu-ai.tar.gz ubuntu@114.132.239.20:/opt/
ssh ubuntu@114.132.239.20
mkdir -p /opt/zhitu-ai && tar -xzf /opt/zhitu-ai.tar.gz -C /opt/zhitu-ai
cd /opt/zhitu-ai
```

> 微信小程序代码（`miniprogram/`）无需上传到服务器，它只在微信开发者工具中编译发布。

---

## 6. 配置环境变量

```bash
cd /opt/zhitu-ai
cp .env.example .env
chmod 600 .env
nano .env          # 按实际情况修改（仓库已附真实可用值，通常无需改）
```

根目录 `.env` 中的关键变量：
- `MYSQL_ROOT_PASSWORD` / `MYSQL_DATABASE` / `REDIS_PASSWORD`：供 `mysql` / `redis` 初始化。
- `JWT_SECRET`：生产务必 `openssl rand -hex 32` 生成随机值。
- `LLM_*` / `VISION_*` / `WX_*` / `SMS_*` / `GAODE_WEB_KEY`：业务密钥（仓库 `.env` 已填真实值）。
- `DATABASE_URL` / `REDIS_URL`：已写成容器内地址（`mysql` / `redis` 主机名），与 `docker-compose.yml` 的 `environment` 双重保险。
- `TICKET_MCP_URL`：留空，走离线估算；如需真实车次，见第 13 节。
- `KB_MILVUS_URI`：向量库地址。**compose 已经把它注入成 `http://milvus:19530` 并优先于 `.env`**，所以根 `.env` 里不用写也写不进去；本地开发才需要在 `server/.env` 填 `kb/corpus/milvus.db`。
  ⚠️ 别在 `.env` 里放裸的 `MILVUS_URI`——那是 pymilvus 自己 import 时读取的变量，填非 http 形式会让后端启动即崩在依赖导入上。
- `KB_MILVUS_COLLECTION`（默认 `kb_docs`）/ `KB_MILVUS_TOKEN`（milvus-lite 留空，官方 Milvus 开了鉴权才填）。

---

## 7. 防火墙与安全组（双层）

**腾讯云轻量控制台 → 防火墙**，仅放行：
- TCP 22（建议限制为你的办公出口 IP）
- TCP 80（HTTP，公网）
- TCP 443（如后续配置 HTTPS）

**服务器 UFW（可选但推荐）：**
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from <办公出口IP>/32 to any port 22 proto tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

**严禁**对公网开放 3306、6379、8000。MySQL 仅绑 `127.0.0.1`，Navicat 必须经 SSH 隧道。

---

## 8. 构建与启动

```bash
cd /opt/zhitu-ai

# 1) 校验 Compose 配置（无输出且退出码 0 即通过）
docker compose config --quiet && echo "compose config OK"

# 2) 构建镜像（首次较慢；前端 Node 堆已限 1024 MB）
docker compose build --pull

# 3) 启动全部服务
docker compose up -d

# 4) ★ 重建 RAG 知识索引（必做，否则问答与行程景点会退回关键词模式）
docker compose exec backend python scripts/build_kb.py

# 5) 确认索引已生效（接口 /api/kb/status 需要 Bearer token，容器内直调更省事）
docker compose exec backend python -c "from kb.retriever import retriever as r; print(r.status())"

# 6) 查看状态
docker compose ps
```

> **为什么第 4 步不能省**：向量集合存在 `milvus_data` 卷里、不进镜像，`server/.dockerignore` 还排除了本地内嵌库 `kb/corpus/milvus.db*` 和旧 flat 产物（`index.vec` / `index.meta.json` / `embed_cache.json`）。跳过重建不会报错——`retriever.client()` 连上 Milvus 但集合是空的，检索静默降级成关键词模式，`r.status()` 显示 `indexed: false` / `engine: keyword`，看起来"上线成功"但 RAG 没生效。第 5 步要看到 `indexed: true` 且 `engine: milvus` 才算数。
>
> **build_kb 写的是远端集合**：`build_kb.py` 在 backend 容器里跑，通过 compose 注入的 `KB_MILVUS_URI=http://milvus:19530` 把向量推给 milvus 容器（milvus-lite 对数据目录加锁，不能让两个进程同时开同一个文件）。所以这一步必须在 `docker compose up -d` 且 milvus 健康之后执行，`--rm` 的一次性容器里跑也一样能连。
>
> ⚠️ **配置项叫 `KB_MILVUS_URI` 而不是 `MILVUS_URI`**：后者被 pymilvus 在自己的 `settings.py` 里 `load_dotenv()` 读走，import 时就解析且只接受 `http[s]://` 形式；在 `.env` 里填本地文件路径会让 `from pymilvus import ...` 直接抛 `ConnectionConfigException`，而我们客户端把这个异常吞成关键词退路——表现就是"配置了却不生效"，极难查。

查看实时日志：
```bash
docker compose logs -f --tail=200
```

> 若服务器内存紧张导致构建失败，先确认第 2 节 swap 已生效，再逐个构建而不是 `docker compose build --pull` 一把梭：
> `docker compose build milvus && docker compose build backend && docker compose build gateway`。
> milvus 镜像首次构建要装 faiss-cpu + pyarrow + grpcio，磁盘下载约 200 MB，但 pip 阶段内存峰值低，真正的风险是三个自研镜像并发构建。

---

## 9. 服务状态检查

```bash
# 容器状态 + 健康状态
docker compose ps
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' $(docker compose ps -q)
```
预期五个服务（mysql / redis / milvus / backend / gateway）均为 `running` 且 `healthy`。

分项验证：
```bash
# 后端健康检查（backend 不对宿主机发布端口，只能进容器打）
docker compose exec backend python -c "import urllib.request as u;print(u.urlopen('http://127.0.0.1:8000/api/health').read().decode())"

# 网关：回环 8081（不是 80，80 被高保真项目占着）
curl -fsS http://127.0.0.1:8081/nginx-health   # 返回 ok
curl -fsS http://127.0.0.1:8081/api/health     # 经网关反代到 backend

# ★ RAG 索引是否已建（跳过第 8 节第 4 步时这里是 false）
docker compose exec backend python -c "from kb.retriever import retriever as r;print(r.status())"

# MySQL / Redis
docker compose exec mysql mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD"
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" ping   # PONG

# 业务库表（应为 8 张；旧库可能残留已废弃的 cities / service_links / chat_history）
docker compose exec mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" zhisuibanyou -e "SHOW TABLES;"'
```

> `/docs`、`/redoc`、`/openapi.json` 在 `app/main.py` 里被显式设为 `None`（上线安全加固，避免接口结构被公开扫描）。**任何"Swagger 可访问"的检查步骤都是错的**，接口清单看 `docs/6-API接口文档.md` 第十节。

资源占用巡检：
```bash
docker stats --no-stream
free -h
df -h /
```

---

## 10. 接口连通性测试

> 服务器 `80` 端口已被「高保真项目」占用，本项目网关只绑 `127.0.0.1:8081`，公网访问由宿主机 Nginx 反代过来。**小程序是唯一用户端，没有网页**：`gateway/nginx.conf` 的 `location /` 直接 `return 404`。所以浏览器打开根路径看到 404 是预期行为，不是部署失败。

1. 网关探活：`curl -fsS http://127.0.0.1:8081/nginx-health` → `ok`。
2. 反代连通：`curl -fsS http://127.0.0.1:8081/api/health` → `{"status":"ok"}`。
3. 接口自检：
   ```bash
   curl -fsS http://127.0.0.1:8081/api/health
   curl -fsS http://127.0.0.1:8081/api/service/list        # 免鉴权，返回渠道白名单
   curl -i http://127.0.0.1:8081/                          # 404 才是对的（无网页端）
   ```
4. 需要 token 的接口（`/api/kb/status`、`/api/user/me` 等）用登录返回的 Bearer 验证，不带 token 应返 401/未授权，**这本身就是鉴权生效的证据**。
5. **微信小程序联调**：将小程序 `config/env.js` 的 `BASE_URL` 改为 `https://<已备案域名>/api`（开发者工具本地联调可用 `http://127.0.0.1:8081` 并关掉 urlCheck），即可走真实后端（HTTPS 与合法域名要求见第 13 节）。注意 `BASE_URL` 末尾不带 `/api`。

---

## 11. 停止 / 重启 / 版本更新

```bash
# 停止（保留容器与数据卷）
docker compose stop

# 启动已停止的服务
docker compose start

# 重启全部
docker compose restart

# 拉新代码并重建应用容器（滚动替换，不删数据卷）
git -C /opt/zhitu-ai pull --ff-only
cd /opt/zhitu-ai
docker compose build --pull backend frontend
docker compose up -d --no-deps backend frontend
docker compose ps

# 首次部署 / 彻底重建
docker compose up -d --build
```

> 删除容器用 `docker compose down`（**默认不删命名卷**）。除非确认数据可丢，否则不要执行 `docker compose down -v`。

---

## 12. 数据初始化

后端 `lifespan` 启动时自动 `create_all` 建表（**8 张**：users / trips / templates / collections / orders / events / feedbacks / distribution_records），并在 `templates` 为空时注入 4 条示例模板。**首次部署不需要任何手工初始化。**

> 2026-10-22 变更：原先设计的 `cities` / `service_links` / `chat_history` 三张表已删除。它们建了但应用代码从不读取——城市列表在前端 `utils/cities.js`（2026-10-23 起从已删除的 `utils/mock.js` 迁出），服务直达渠道硬编码在 `routers/service.py` 的 `SERVICES`，问答是流式返回不落库。本节的「mysqldump 导种子 / 手工 INSERT 城市」步骤因此作废。
>
> 旧库里这三张空表可能仍残留（`create_all` 不会 DROP）。确认无外部依赖后可自行清理，**本指南不在共享演示库上代为执行**：
> ```sql
> DROP TABLE IF EXISTS chat_history, service_links, cities;
> ```

`server/db_init.py` 是给开发机用的同步建表脚本（走 `mysql+pymysql`，依赖 `PyMySQL` 与 `python-dotenv`，两者都未写进 `requirements.txt`），容器内不要执行——镜像里的异步 `DATABASE_URL` 与它不兼容，且它的能力已被启动时的 `create_all` 覆盖。

---

## 13. 上线前必读（小程序生产约束）

1. **必须 HTTPS + 域名**：微信小程序 `request` 合法域名**不支持裸 IP**，必须是已备案域名且 HTTPS。请在 Nginx 前置终止 TLS（证书可用腾讯云 SSL 或 Let's Encrypt），并把 80 重定向到 443，再在微信公众平台配置 `https://你的域名` 为 request 合法域名。
2. **12306 真实车次（可选）**：本镜像 `TICKET_MCP_URL` 默认留空（离线估算）。如需真实车次，在宿主机运行 `npx -y 12306-mcp --port 8801`，并在 `docker-compose.yml` 的 `backend` 增加：
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   environment:
     TICKET_MCP_URL: "http://host.docker.internal:8801/mcp"
   ```
3. **微信支付**：会员订阅闭环需在企业/个体户主体下开通微信支付商户号，并把 `WX_MCH_ID` / `WX_API_V3_KEY` 填入 `.env`。
4. **密钥安全**：`.env` 已 `chmod 600`，切勿提交 Git；JWT/数据库/Redis 密码生产与开发务必不同。

---

## 14. 常见故障排查清单

| 现象 | 排查命令 | 常见原因 / 处理 |
| --- | --- | --- |
| MySQL 一直 `starting`/`unhealthy` | `docker compose logs mysql` | 首次初始化慢 / 磁盘满；勿删卷，等其就绪 |
| 后端连不上数据库 | `docker compose logs backend`；`docker compose exec backend env \| grep DB` | `DATABASE_URL` 主机名须为 `mysql` 而非 `localhost`；检查 `.env` 密码一致 |
| 页面能开但 `/api` 失败 | `curl -i http://127.0.0.1/api/health`；`docker compose logs frontend` | Nginx `proxy_pass` 指向 `backend:8000`；重建 frontend |
| 上传返回 413 | `docker compose logs frontend` | Nginx `client_max_body_size` 上限；如需调大同步改 Nginx 与业务限制 |
| 内存不足 / OOM | `free -h`；`swapon --show`；`docker stats` | 确认 1G swap 已挂载；`docker builder prune` 清理构建缓存 |
| Redis 启动失败 | `docker compose logs redis` | 密码含特殊字符需转义；`--maxmemory` 参数格式 |
| 前端构建 `heap out of memory` | `free -h` | 未开 swap 或堆上限过低；开 swap 后重建 |
| Navicat 连不上 MySQL | `docker compose ps mysql`；`docker port $(docker compose ps -q mysql)`；`sudo ss -lntp \| grep 3307` | 必须 `127.0.0.1:3307` 已发布；用 SSH 隧道（主机 114.132.239.20:22 + 本地 127.0.0.1:3307） |
| 容器启动报 `bind: address already in use` | `sudo ss -lntp \| grep -E ':(80\|8081\|3306\|3307)'` | 与服务器上已有项目（如高保真）端口冲突；修改 `.env` 里的 `FRONTEND_PORT` / `MYSQL_HOST_PORT` 后重建容器 |
| 容器日志占满磁盘 | `docker system df` | 配置 Docker 日志轮转（见第 15 节） |

---

## 15. 备份与日志轮转建议

**数据库每日备份（手动示例）：**
```bash
docker compose exec backend sh -c \
  'mysqldump -hmysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --single-transaction zhisuibanyou > /tmp/zt_$(date +%Y%m%d).sql'
docker compose cp backend:/tmp/zt_$(date +%Y%m%d).sql ./backup/
```
> 生产建议把备份同步到腾讯云 COS，不要只留在本机 40 GB 系统盘。

**Docker 日志轮转**（防止 JSON 日志写满磁盘），在服务器 `/etc/docker/daemon.json`：
```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
```
改完 `sudo systemctl restart docker`（会重启容器，请先 `docker compose stop`）。

---

## 16. 交付物清单

| 文件 | 说明 |
| --- | --- |
| `docker-compose.yml` | 四服务编排，含资源限制 / 健康检查 / 网络隔离 / 命名卷 |
| `server/Dockerfile` | Python 3.11-slim，内置阿里云 PyPI 源，单 worker |
| `server/.dockerignore` | 排除 `.env` / `venv` / 缓存 |
| `frontend/Dockerfile` | 多阶段：Node 构建 dist + Nginx 运行，镜像优化 |
| `frontend/nginx.conf` | 静态托管 + `/api` 反代 `backend:8000` + `/nginx-health` |
| `frontend/`（Vue3 源码） | 运营/自检面板，`npm run build` 产物即 dist |
| `.env` / `.env.example` | 部署环境变量（真实值已填，生产请换随机密钥） |
| `docs/知途AI Docker部署指南.md` | 本文件 |

部署完成后，浏览器访问 `http://114.132.239.20:8081/` 即可看到服务状态面板；小程序端将 `BASE_URL` 指向 `http://114.132.239.20:8081/api`（生产需域名 + HTTPS）即可联调真实后端。

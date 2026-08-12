# 知途 AI 旅行 · Docker Compose 全栈部署指南

> 适用环境：腾讯云轻量应用服务器 **2 vCPU / 2 GB / 40 GB SSD / 3 Mbps（月流量 200 GB）/ Ubuntu Server 24.04 LTS / Docker 27.5.1**
> 本文档基于项目真实源码（FastAPI 后端 + MySQL + Redis）生成，并参照《Docker Compose 部署参考文档》的约束落地。

---

## 1. 部署架构与范围

| 服务 | 镜像 | 作用 | 对外暴露 |
| --- | --- | --- | --- |
| `mysql` | mysql:8.0 | 业务数据库 `zhisuibanyou` | 仅 `127.0.0.1:3306`（SSH 隧道用） |
| `redis` | redis:7-alpine | 缓存 / 限流 / 扩展能力 | 仅 Compose 内网 |
| `backend` | 自构建（python:3.11-slim） | FastAPI 接口、AI 规划、OCR、问答 | 仅内网 `8000` |
| `frontend` | 自构建（nginx:alpine） | Vue3 运营/自检面板 + 反代 `/api` | 公网 `80` |

> **关于「前端」说明**：本项目的真实用户端是**微信小程序**（由微信平台托管，不进容器）。此处 `frontend` 是一个轻量 Vue3 面板，用于展示后端与依赖健康状态、提供 `/docs` 接口文档入口，并通过 Nginx 把 `/api/*` 反代到 `backend:8000`。这样既满足「Vue3 前端 Dockerfile（基于 dist）+ Nginx 站点配置」的交付要求，又完整跑通全栈。

网络隔离：
- `backend_net`：`mysql` / `redis` / `backend` 互通，不暴露公网。
- `frontend_net`：`frontend` / `backend` 互通，`frontend` 向公网开放 80。

持久化卷：`mysql_data`（数据库文件）、`redis_data`（AOF 数据）。

---

## 2. 资源规划（2 核 2 GB 关键约束）

| 服务 | mem_limit | mem_reservation | cpus | 说明 |
| --- | --- | --- | --- | --- |
| mysql | 800 m | 600 m | 1.0 | `innodb-buffer-pool-size=256M` 压内存 |
| redis | 256 m | 160 m | 0.5 | `--maxmemory 200mb` 硬性淘汰 |
| backend | 512 m | 256 m | 1.0 | `UVICORN_WORKERS=1` 单进程 |
| frontend | 128 m | 64 m | 0.5 | Nginx 静态 + 反代，极轻 |
| **合计上限** | **~1.7 GB** | **~1.08 GB** | **3.0** | 预留余量给 OS 与峰值 |

- CPU 配额总和 3.0 > 2 核：靠 `cpus` 软限制避免单服务独占，非硬性隔离。
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
├── server/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── app/
│   └── ...
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── .dockerignore
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
```

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
    --exclude='miniprogram' --exclude='.git' --exclude='outputs' --exclude='UI导出' \
    -czf zhitu-ai.tar.gz docker-compose.yml .env.example server frontend
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

# 4) 查看状态
docker compose ps
```

查看实时日志：
```bash
docker compose logs -f --tail=200
```

> 若服务器内存紧张导致前端构建失败（`JavaScript heap out of memory`），确认第 2 节 swap 已生效，再 `docker compose build --no-cache frontend`。

---

## 9. 服务状态检查

```bash
# 容器状态 + 健康状态
docker compose ps
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' $(docker compose ps -q)
```
预期四个服务均为 `running` 且 `healthy`。

分项验证：
```bash
# 后端健康检查（新增 /api/health）
curl -fsS http://127.0.0.1/api/health        # 返回 {"status":"ok"}
curl -fsS http://127.0.0.1/api/docs >/dev/null   # Swagger 文档可访问

# 前端面板
curl -I http://127.0.0.1/
curl -fsS http://127.0.0.1/nginx-health      # 返回 ok

# MySQL / Redis
docker compose exec mysql mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD"
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" ping   # PONG

# 业务库表
docker compose exec mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" zhisuibanyou -e "SHOW TABLES;"'
```

资源占用巡检：
```bash
docker stats --no-stream
free -h
df -h /
```

---

## 10. 公网 IP 访问测试

1. 浏览器打开 `http://114.132.239.20/`，应看到「知途 AI 旅行 · 服务状态」面板。
2. 点击「重新检测」，后端 API 状态应显示「正常」。
3. 打开 `http://114.132.239.20/docs`，确认 Swagger 接口文档可加载。
4. 命令行接口自检：
   ```bash
   curl -fsS http://114.132.239.20/api/health
   curl -fsS http://114.132.239.20/api/openapi.json >/dev/null
   ```
5. **微信小程序联调**：将小程序 `config/env.js` 的 `BASE_URL` 改为 `http://114.132.239.20/api`，`USE_MOCK=false`，即可在开发者工具中走真实后端（注意第 13 节的 HTTPS/合法域名要求）。

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

## 12. 数据初始化（城市 / 服务种子）

后端 `lifespan` 会自动 `create_all` 建表，并注入**模板广场**种子（`template_service.seed()`）。但**城市表（cities）/ 服务表（service_links）** 在代码中无自动种子逻辑（原开发库由 `db_init.py` 导入，而该脚本使用同步引擎，与本镜像的异步 `DATABASE_URL` 不兼容，容器内勿直接运行）。

首次部署后请二选一补齐基础数据：

**方式 A：从现有开发库导出导入（数据最完整，推荐）**
```bash
# 在「已有数据的开发机」导出
mysqldump -uroot -p zhisuibanyou cities service_links > seed.sql
# 传到服务器并导入新容器
scp seed.sql ubuntu@114.132.239.20:/opt/
ssh ubuntu@114.132.239.20
docker compose exec -T mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" zhisuibanyou' < /opt/seed.sql
```

**方式 B：手动插入最小可用数据**（示例，按需扩展）
```bash
docker compose exec -T mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" zhisuibanyou' <<'SQL'
INSERT INTO cities (name, province, hot) VALUES
  ('杭州','浙江',1),('成都','四川',1),('西安','陕西',1),('苏州','江苏',1),
  ('重庆','重庆',1),('厦门','福建',1),('长沙','湖南',1),('南京','江苏',1);
SQL
```

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
| Navicat 连不上 MySQL | `docker compose ps mysql`；`docker port $(docker compose ps -q mysql)`；`sudo ss -lntp \| grep 3306` | 必须 `127.0.0.1:3306` 已发布；用 SSH 隧道（主机 114.132.239.20:22 + 本地 127.0.0.1:3306） |
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

部署完成后，浏览器访问 `http://114.132.239.20/` 即可看到服务状态面板；小程序端将 `BASE_URL` 指向该地址（生产需域名 + HTTPS）即可联调真实后端。

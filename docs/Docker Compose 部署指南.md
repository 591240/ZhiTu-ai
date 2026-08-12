# 智能文件管理助手 Docker Compose 部署指南

本文档适用于腾讯云 Ubuntu Server 24.04 LTS 64bit、2 vCPU、2 GB RAM、40 GB SSD，并针对 Docker Engine 27.5.1 和 Docker Compose V2 编写。

## 1. 架构与部署范围

项目源码分析得到的生产服务：

| 服务 | 作用 | 对外暴露 |
| --- | --- | --- |
| `frontend` | Vue 生产构建产物和 Nginx 反向代理 | TCP 80 |
| `backend` | FastAPI API、文件处理、定时清理和数据库备份 | 仅 Compose 内网 |
| `mysql` | MySQL 8 业务数据库 | 仅绑定宿主机 `127.0.0.1:3306`，供 SSH 隧道/本机访问 |
| `redis` | Redis 缓存配置，当前代码主要保留扩展能力 | 仅 Compose 内网 |

参考文档中的 RabbitMQ 和 Elasticsearch 未加入本方案：当前项目依赖和源码没有实际使用这两个组件。在 2 核 2 GB 服务器上不运行无实际依赖的基础设施，可以显著降低内存压力。

网络隔离：

- `frontend_net`：前端可访问后端，前端容器连接此网络。
- `backend_net`：后端可访问 MySQL 和 Redis，不直接暴露到公网。
- MySQL 数据仍存储在 Docker 命名卷 `sfma_mysql_data` 中；容器端口 `3306` 仅映射到宿主机回环地址 `127.0.0.1:${MYSQL_TUNNEL_PORT:-3306}`，用于 Navicat 通过 SSH 隧道查看业务库。
- Redis 使用内部网络，不映射宿主机端口。

持久化卷：

- `sfma_mysql_data`：数据库文件。
- `sfma_redis_data`：Redis AOF 数据。
- `sfma_uploads_data`：用户上传文件、分片和 ZIP 文件。
- `sfma_backups_data`：应用每日数据库备份。
- `sfma_backend_logs`：后端日志文件。

## 2. 前置条件检查

### 2.1 登录服务器

```bash
ssh <云服务器用户名>@43.139.5.234
```

建议使用普通运维用户，并确保该用户已加入 `docker` 用户组。不要把数据库端口、Redis 端口或后端 8000 端口直接开放到公网；MySQL 的 `3306` 只允许绑定在服务器本机 `127.0.0.1`，供 SSH 隧道访问。

### 2.2 检查系统与资源

```bash
cat /etc/os-release
uname -m
nproc
free -h
df -h /
timedatectl
```

预期：

- Ubuntu 版本为 24.04 LTS。
- 架构为 `x86_64`。
- CPU 为 2 核，内存约 2 GB。
- 根分区剩余空间应足够构建镜像和保存上传文件。
- 时区建议为 `Asia/Shanghai`，Compose 服务已设置 `TZ=Asia/Shanghai`。

40 GB 磁盘需要重点监控上传文件、MySQL 数据、镜像和备份。不要无限期保留 Docker 构建缓存和数据库备份。

### 2.3 检查 Docker 版本

```bash
docker --version
docker compose version
docker info
```

目标版本：

```text
Docker version 27.5.1
Docker Compose version v2.x
```

Docker Compose V2 的命令是 `docker compose`，不是旧版独立命令 `docker-compose`。如果当前用户无权限：

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker ps
```

## 3. 获取源码与目录结构

### 3.1 获取源码

将 `<repository-url>` 替换为实际 Git 仓库地址：

```bash
sudo mkdir -p /opt
sudo chown "$USER":"$USER" /opt
git clone <repository-url> /opt/smart-file-management-assistant
cd /opt/smart-file-management-assistant
```

如果使用压缩包，将项目完整解压到 `/opt/smart-file-management-assistant`，并确认 `docker-compose.yml` 位于项目根目录。

### 3.2 目录结构

```text
项目根目录/
├── docker-compose.yml
├── .env.example
├── .dockerignore
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   └── scripts/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── nginx-main.conf
│   ├── package.json
│   ├── package-lock.json
│   └── src/
└── docs/
    ├── Docker Compose 部署参考文档.md
    └── Docker Compose 部署指南.md
```

## 4. 配置环境变量

复制模板并编辑：

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

必须修改的变量：

| 变量 | 说明 |
| --- | --- |
| `SECRET_KEY` | 应用密钥，生产环境必须使用随机值 |
| `JWT_SECRET_KEY` | JWT 签名密钥，必须与 `SECRET_KEY` 不同 |
| `MYSQL_PASSWORD` | 应用数据库用户密码 |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码，仅用于数据库初始化和健康检查 |
| `MYSQL_TUNNEL_PORT` | MySQL 宿主机回环映射端口，默认 `3306`，用于 Navicat SSH 隧道 |

本方案默认在构建后端镜像时使用阿里云 PyPI HTTPS 镜像：

```text
https://mirrors.aliyun.com/pypi/simple/
```

根目录 `.env` 中的 `PIP_INDEX_URL` 可覆盖该地址。构建时通过 Docker `build.args` 传入，仅影响镜像构建阶段的 `pip install`，不会把该变量作为后端运行时配置。

生成随机密钥示例：

```bash
openssl rand -hex 32
```

资源限制建议：

- `WORKERS=1`：2 核 2 GB 服务器不建议启动多个 Uvicorn worker。
- `DB_POOL_SIZE=5`、`DB_MAX_OVERFLOW=2`：避免 MySQL 连接池占用过多资源。
- `MAX_FILE_SIZE=104857600`：单文件 100 MB，和前端功能保持一致。
- `HTTP_PORT=80`：如果 80 端口被其他程序占用，可改为 `8080`。

前端构建默认使用 `VITE_API_BASE=/api/v1`，由 Nginx 将 `/api/` 代理到 `backend:8000`，因此通常不需要填写公网 IP。若将来前后端分域名，再在构建时传入对应 API 地址。

## 5. 腾讯云安全组与 Ubuntu 防火墙

腾讯云安全组建议只放行：

- TCP 22：仅允许办公出口 IP。
- TCP 80：允许公网访问。
- TCP 443：配置 HTTPS 后允许公网访问。

Ubuntu 上可使用 UFW：

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from <办公出口IP>/32 to any port 22 proto tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

不要在腾讯云安全组或 UFW 中对公网开放 3306、6379、8000、15672、9200 等不属于本项目公网入口的端口。MySQL 的 `3306` 仅绑定 `127.0.0.1`，外网无法直连；Navicat 必须通过 SSH 隧道访问。

| 命令                                                         | 含义                                                         |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| `sudo ufw default deny incoming`                             | **默认拒绝所有入站流量**（即外部主动访问本机的连接都会被阻止） |
| `sudo ufw default allow outgoing`                            | **默认允许所有出站流量**（即本机主动对外发起的连接正常放行） |
| `sudo ufw allow from <办公出口IP>/32 to any port 22 proto tcp` | **仅允许指定办公 IP 访问本机的 SSH（22 端口）**，`/32` 表示精确匹配单个 IP |
| `sudo ufw allow 80/tcp`                                      | **允许外部访问本机的 HTTP（80 端口）**                       |
| `sudo ufw allow 443/tcp`                                     | **允许外部访问本机的 HTTPS（443 端口）**                     |
| `sudo ufw enable`                                            | **启用防火墙规则**（使上述配置正式生效）                     |
| `sudo ufw status verbose`                                    | **查看防火墙的详细状态**（显示当前启用的规则、默认策略等）   |





## 6. 构建、启动和生命周期命令

在项目根目录执行。

### 6.1 校验 Compose 配置

```bash
docker compose config
docker compose config --quiet
```

第二条命令没有输出且退出码为 0 时，表示 Compose 配置解析成功。

### 6.2 构建镜像

```bash
docker compose build --pull
```

首次构建可能需要较长时间。前端采用 Node 构建阶段 + Nginx 运行阶段，后端只安装生产依赖和 `mysqldump` 所需的 MySQL 客户端。

前端锁文件曾包含与 Node 22 内置 npm 的可选 peer 依赖解析不一致项。`frontend/Dockerfile` 已使用 `npm ci --ignore-scripts --legacy-peer-deps` 保持锁文件的严格安装方式，同时避免该解析差异导致 `picomatch` 相关的 `EUSAGE` 构建失败。

由于服务器只有 2 GB 内存，前端 Docker 构建阶段已将 Node.js 堆上限设置为 1536 MB。首次构建前建议确保服务器有至少 1 GB swap，且不要在构建时同时运行不必要的高内存进程。

### 6.3 启动服务

```bash
docker compose up -d
docker compose ps
```

查看启动过程：

```bash
docker compose logs -f --tail=200
```

### 6.4 停止、重启和更新

```bash
# 停止但保留容器和数据卷
docker compose stop

# 启动已停止的服务
docker compose start

# 重启全部服务
docker compose restart

# 拉取新代码、重建并滚动替换应用容器
git pull --ff-only
docker compose build --pull backend frontend
docker compose up -d --no-deps backend frontend
docker compose ps
```

如果服务器不是通过 Git 获取源码，而是手工上传项目，请至少重新上传以下文件后再构建：

```text
frontend/Dockerfile
frontend/package.json
frontend/package-lock.json
docs/Docker Compose 部署指南.md
```

首次部署或需要重新创建所有容器时：

```bash
docker compose up -d --build
```

### 6.5 删除容器

```bash
docker compose down
```

默认不会删除命名卷。除非确认不再需要数据，否则不要执行：

```bash
docker compose down -v
```

## 7. 健康检查与状态验证

### 7.1 容器状态

```bash
docker compose ps
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' \
  $(docker compose ps -q)
```

预期 `mysql`、`redis`、`backend`、`frontend` 均为 `running`，并且健康状态为 `healthy`。

### 7.2 后端 API

```bash
curl -fsS http://127.0.0.1/api/health
curl -fsS http://127.0.0.1/api/docs >/dev/null
```

预期第一条返回：

```json
{"status":"ok"}
```

容器内部验证：

```bash
docker compose exec backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read().decode())"
```

### 7.3 前端

```bash
curl -I http://127.0.0.1/
curl -fsS http://127.0.0.1/nginx-health
```

浏览器访问：

```text
http://43.139.5.234/
```

如果使用域名，将域名 A 记录解析到服务器公网 IP 后访问域名。

### 7.4 数据库和 Redis

```bash
docker compose exec mysql mysqladmin ping -h 127.0.0.1 -u root -p
docker compose exec redis redis-cli ping
```

输入 root 密码后，MySQL 应返回 `mysqld is alive`，Redis 应返回 `PONG`。

验证业务库和数据表：

```bash
docker compose exec mysql sh -lc \
  'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SHOW TABLES;"'
```

验证给 Navicat SSH 隧道使用的宿主机回环端口：

```bash
docker compose ps mysql
docker port "$(docker compose ps -q mysql)"
sudo ss -lntp | grep ':3306'
set -a; . ./.env; set +a
mysql -h127.0.0.1 -P"${MYSQL_TUNNEL_PORT:-3306}" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SHOW TABLES;"
```

`docker compose ps mysql` 的 `PORTS` 列应出现 `127.0.0.1:3306->3306/tcp`。如果 `PORTS` 为空，说明 MySQL 容器没有发布宿主机回环端口，Navicat 通过 SSH 隧道也无法连接。

### 7.5 Navicat 通过 SSH 隧道连接 Docker MySQL

本项目的业务数据存储在 Docker Compose MySQL 容器的数据卷 `sfma_mysql_data` 中。Navicat 不应直连公网 `43.139.5.234:3306`，也不应连接宿主机上额外安装的 MySQL；应通过 SSH 隧道连接服务器本机回环端口。

Navicat `常规` 页：

```text
主机：127.0.0.1
端口：3306
用户名：.env 中 MYSQL_USER 的值，例如 sfma
密码：.env 中 MYSQL_PASSWORD 的值
数据库：.env 中 MYSQL_DATABASE 的值，例如 smart_file_management_assistant
```

Navicat `SSH` 页：

```text
使用 SSH 隧道：勾选
主机：43.139.5.234
端口：22
用户名：ubuntu
密码：服务器 ubuntu 用户密码或对应私钥
```

如果服务器宿主机曾经安装过 MySQL，请停止并禁用宿主机 MySQL，避免它占用 `127.0.0.1:3306`：

```bash
sudo systemctl stop mysql || true
sudo systemctl disable mysql || true
```

## 8. 前端访问与后端 API 验证流程

1. 浏览器打开 `http://<服务器公网IP>/`，确认登录页能加载。
2. 打开浏览器开发者工具 Network，确认 `/api/health`、`/api/v1/...` 请求返回 2xx 或业务预期状态码。
3. 在注册页创建一个测试用户。
4. 使用测试用户登录，确认 Token 写入浏览器本地存储。
5. 创建文件夹并上传一个小文件，确认列表能看到文件。
6. 下载或预览该文件，确认文件内容正确。
7. 删除并恢复文件，确认回收站流程正常。

命令行接口测试：

```bash
curl -fsS http://43.139.5.234/api/health
curl -fsS http://43.139.5.234/api/openapi.json >/dev/null
curl -sS -X POST http://43.139.5.234/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"deploy_check","password":"ChangeMe_123456","email":"deploy_check@example.com"}'
curl -sS -X POST http://43.139.5.234/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"deploy_check","password":"ChangeMe_123456"}'
```

不要在共享终端、工单或日志中保存登录响应里的 JWT。

## 9. 日志与问题排查

### 9.1 查看日志

```bash
docker compose logs --tail=200 frontend
docker compose logs --tail=200 backend
docker compose logs --tail=200 mysql
docker compose logs --tail=200 redis
docker compose logs -f backend
```

后端文件日志位于命名卷中：

```bash
docker compose exec backend sh -c 'ls -lh /app/logs'
```

### 9.2 常用诊断

```bash
docker compose ps
docker compose config
docker system df
df -h
free -h
docker stats --no-stream
docker compose port frontend 80
```

由于 Nginx 在容器内以非 root 用户监听 `8080`，对应检查命令为：

```bash
docker compose port frontend 8080
```

### 9.3 重新构建单个应用

```bash
docker compose build --no-cache backend
docker compose up -d --no-deps backend

docker compose build --no-cache frontend
docker compose up -d --no-deps frontend
```

## 10. 常见问题

### 10.1 `MYSQL_ROOT_PASSWORD is required`

根目录没有 `.env`，或变量为空。执行：

```bash
cp .env.example .env
nano .env
docker compose config --quiet
```

### 10.2 前端构建报 `npm ci`、`picomatch` 或 `EUSAGE`

这表示前端依赖树在当前 npm 版本下遇到了可选 peer 依赖解析差异。请先确认服务器使用了项目最新的 `frontend/Dockerfile`：

```bash
grep 'npm ci' frontend/Dockerfile
```

预期命令包含：

```text
npm ci --ignore-scripts --legacy-peer-deps
```

然后清除前端构建缓存并重建：

```bash
docker compose build --no-cache frontend
docker compose up -d --no-deps frontend
```

### 10.3 MySQL 一直不是 healthy

查看日志：

```bash
docker compose logs mysql
```

常见原因是首次初始化时间较长、磁盘空间不足或旧数据卷中的密码与 `.env` 不一致。已有数据卷不会因为修改环境变量而重新设置密码，切勿直接删除卷；应使用原密码登录后单独修改账户密码。

### 10.4 后端连接数据库失败

确认 `.env` 中的 `MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE` 与首次初始化数据库时的值一致，并检查：

```bash
docker compose exec backend env | grep -E 'DB_HOST|DB_USER|DB_NAME'
docker compose logs backend
```

Compose 内部连接地址必须使用 `mysql`，不能使用 `localhost`。

### 10.5 Navicat SSH 隧道连接 Docker MySQL 失败

如果 Navicat 报：

```text
2013 - Lost connection to server at 'handshake: reading initial communication packet'
ERROR 2003 (HY000): Can't connect to MySQL server on '127.0.0.1:3306' (111)
```

先在服务器确认 MySQL 容器是否真的发布到宿主机回环端口：

```bash
cd /home/ubuntu/management-assistant
docker compose config | sed -n '/mysql:/,/redis:/p'
docker compose ps mysql
docker port "$(docker compose ps -q mysql)"
sudo ss -lntp | grep ':3306' || true
```

`docker compose config` 中应包含：

```yaml
ports:
  - mode: ingress
    host_ip: 127.0.0.1
    target: 3306
    published: "3306"
    protocol: tcp
```

`docker compose ps mysql` 的 `PORTS` 列应包含 `127.0.0.1:3306->3306/tcp`。如果配置中有 `ports`，但容器实际 `PORTS` 为空，通常是旧容器未重建或数据网络仍配置为 `internal: true`。处理方式：

```bash
cd /home/ubuntu/management-assistant
sudo systemctl stop mysql || true
sudo systemctl disable mysql || true
docker compose down
docker compose up -d
docker compose ps mysql
docker port "$(docker compose ps -q mysql)"
```

注意不要执行 `docker compose down -v`，否则会删除 MySQL 数据卷。

如果 Navicat 报：

```text
1045 - Access denied for user 'sfma'@'localhost'
```

说明端口已经连通，但 MySQL 用户密码或授权不匹配。`.env` 里的 `MYSQL_PASSWORD` 只在 MySQL 数据卷首次初始化时生效，后续修改 `.env` 不会自动修改已存在用户的密码。可用 root 在容器内修正：

```bash
docker compose exec mysql sh -lc \
  'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "ALTER USER '\''sfma'\''@'\''%'\'' IDENTIFIED BY '\''root123'\''; GRANT ALL PRIVILEGES ON smart_file_management_assistant.* TO '\''sfma'\''@'\''%'\''; FLUSH PRIVILEGES;"'
```

再验证：

```bash
docker compose exec mysql sh -lc \
  'mysql -usfma -proot123 "$MYSQL_DATABASE" -e "SHOW TABLES;"'
```

### 10.6 后端启动报 `email-validator is not installed`

如果日志出现：

```text
ImportError: email-validator is not installed
```

说明后端镜像使用了旧依赖层。同步最新源码后，重新构建后端：

```bash
git pull --ff-only
docker compose build --no-cache backend
docker compose up -d --no-deps backend
docker compose ps
docker compose logs --tail=100 backend
```

项目已将 `email-validator>=2.2.0` 加入 `backend/pyproject.toml`，用于支持注册接口中的邮箱格式校验。

### 10.7 后端启动报 `/app/logs` 的 `Permission denied`

如果日志出现：

```text
PermissionError: [Errno 13] Permission denied: '/app/logs/app_YYYY-MM-DD.log'
```

这是 Docker 命名卷首次挂载时由 root 创建目录，而后端应用以非 root 用户运行造成的。同步最新 `backend/Dockerfile` 和 `backend/docker-entrypoint.sh` 后重建后端：

```bash
git pull --ff-only
docker compose build --no-cache backend
docker compose up -d --no-deps backend
docker compose ps
docker compose logs --tail=100 backend
```

入口脚本会在启动时只对应用实际写入的挂载目录设置所有者，再以 `app` 用户运行 Uvicorn。不要通过把整个后端容器改为 root 来规避该问题。

### 10.8 页面能打开但 API 失败

确认后端健康：

```bash
curl -i http://127.0.0.1/api/health
docker compose logs frontend backend
```

如果宿主机执行 `curl http://127.0.0.1/api/health` 报 `Failed to connect`，先检查前端容器：

```bash
docker compose ps
docker compose logs --tail=200 frontend
docker compose run --rm frontend nginx -t
```

本方案的 Nginx 容器以非 root 用户运行，容器内监听 `8080`，宿主机仍通过 `HTTP_PORT` 映射到 `80`。如果日志提示 PID 或临时目录权限问题，请同步最新的 `frontend/Dockerfile`、`frontend/nginx.conf` 和 `frontend/nginx-main.conf` 后重建：

```bash
docker compose build --no-cache frontend
docker compose up -d --no-deps frontend
docker compose ps
curl -fsS http://127.0.0.1/nginx-health
curl -fsS http://127.0.0.1/api/health
```

确认 Nginx 配置中的 upstream 为 `backend:8000`，并重新构建前端：

```bash
docker compose build frontend
docker compose up -d --no-deps frontend
```

### 10.9 上传返回 413

Nginx 已设置 `client_max_body_size 110m`。如果要提高单文件限制，需要同步修改 `.env` 的 `MAX_FILE_SIZE`、Nginx 的 `client_max_body_size`，并重新构建前端。2 GB 内存服务器不建议盲目提高并发和单文件大小。

### 10.10 上传文件或备份重启后消失

确认使用了命名卷，并且没有执行 `docker compose down -v`：

```bash
docker volume ls | grep sfma
docker compose config
```

### 10.11 服务器内存不足或磁盘不足

```bash
docker stats --no-stream
docker system df
df -h
```

清理无用构建缓存：

```bash
docker builder prune
```

仅在确认无用镜像后再清理：

```bash
docker image prune
```

不要使用会删除业务卷的清理命令。

如果构建日志出现 `JavaScript heap out of memory`，先检查内存和 swap：

```bash
free -h
swapon --show
```

没有 swap 时，可创建 1 GB swap：

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
free -h
```

然后重新构建前端：

```bash
docker compose build --no-cache frontend
docker compose up -d --no-deps frontend
```

### 10.11 管理员账号问题

当前源码的注册接口默认创建普通用户，没有实现 README 中提到的自动初始化管理员模块。首次部署后应先注册普通账号；如确需管理员账号，应在备份数据库后由受控 SQL 或后续管理脚本将对应用户的 `role` 设置为 `admin`，不要把管理员密码写入镜像或 Compose 文件。

### 10.12 注册或登录报 `password cannot be longer than 72 bytes`

如果后端日志出现：

```text
ValueError: password cannot be longer than 72 bytes
```

请同步最新 `backend/pyproject.toml` 和 `backend/app/schemas/user.py` 后，重新构建后端：

```bash
git pull --ff-only
docker compose build --no-cache backend
docker compose up -d --no-deps backend
docker compose logs --tail=100 backend
```

本项目固定使用 `bcrypt>=4.3.0,<5.0.0`，以兼容当前 `passlib 1.7.4`。同时，注册和修改密码接口会校验 UTF-8 编码后的密码长度不超过 72 字节；超过时将返回 422 参数校验错误，而不是保存被截断的密码。

## 11. 备份与恢复

应用会在每日 03:30 尝试使用 `mysqldump` 写入 `/app/logs` 对应的数据库备份目录 `/data/backups`。

手动备份：

```bash
docker compose exec backend sh -c \
  'mysqldump -hmysql -P3306 -u"$DB_USER" -p"$DB_PASSWORD" --default-character-set=utf8mb4 --single-transaction "$DB_NAME" > "/data/backups/manual_$(date +%Y%m%d_%H%M%S).sql"'
```

查看备份：

```bash
docker compose exec backend ls -lh /data/backups
```

恢复前必须停止写入业务并确认备份文件来源：

```bash
docker compose exec -T mysql sh -c \
  'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' < backup.sql
```

生产环境建议把关键备份同步到腾讯云 COS 或其他独立存储，不能只保留在同一块 40 GB 系统盘上。

## 12. 安全加固建议

- 仅暴露 Nginx 的 80/443，数据库、Redis、后端端口保持内网。
- 配置腾讯云安全组和 UFW 双层限制，SSH 只允许固定办公 IP。
- 使用高强度且互不相同的 `MYSQL_PASSWORD`、`MYSQL_ROOT_PASSWORD`、`SECRET_KEY` 和 `JWT_SECRET_KEY`。
- `.env` 设置为 `chmod 600`，不要提交 Git，不要在工单和聊天中粘贴。
- 应用容器使用非 root 用户，Compose 使用 `no-new-privileges`。
- 生产环境 `DEBUG=false`、`WORKERS=1`，避免调试信息和过量进程消耗内存。
- 定期升级基础镜像并执行 `docker compose build --pull`，升级前先备份数据库和上传文件。
- 使用 HTTPS。可在前置负载均衡、腾讯云 SSL 证书服务或独立反向代理中终止 TLS。
- 为 Docker 日志设置轮转策略，防止 JSON 日志占满 40 GB 磁盘。
- 监控 `docker stats`、`df -h`、MySQL 健康状态和备份文件生成情况。
- 生产升级时保留旧镜像和可回滚的 Git commit，确认健康检查通过后再清理旧资源。

## 13. 后续扩展

当前 Compose 已将应用和基础设施分层，后续可按实际代码依赖增加：

- 独立 worker 容器，用于大文件 ZIP、异步索引等耗时任务。
- Redis 分布式限流和任务状态存储。
- 对象存储（腾讯云 COS）替代本地上传卷。
- HTTPS 网关、域名、监控和集中式日志。
- MySQL 主从或托管数据库，减少单机故障风险。

新增服务时应单独声明网络、健康检查、持久化卷、资源上限和敏感变量，不要默认把所有端口映射到公网。

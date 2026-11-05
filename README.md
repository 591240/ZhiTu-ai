# 知途 AI 旅行 · AI 智能短途行程规划小程序

> 面向 1-4 天短途自由行用户的 AI 行程规划工具：四种创建方式（表单 / 一句话 / 截图 / 手动）、大众+小众双路线、旅游智能问答、第三方服务快捷跳转。
> 产品原名「智随伴游」（曾用名「伴游」），现已统一更名为 **知途 AI 旅行**。

---

## 项目结构

```
知途 AI 旅行/
├── miniprogram/        # 微信原生小程序前端（WXML/WXSS/JS）
│   ├── pages/          # 22 个页面（首页/登录/表单/一句话/截图识行程/详情/行程/对话/模板/收藏/会员/个人中心/...）
│   ├── components/     # 自定义组件（route-tag 等）
│   ├── utils/          # request / storage / auth / format / cities / error
│   ├── config/env.js   # 环境配置：BASE_URL、MONETIZATION_ENABLED、服务跳转白名单
│   └── app.json        # 全局配置 + tabBar（首页/我的行程/我的）
├── server/             # FastAPI 后端（本地 3.13，镜像基础为 `python:3.11-slim`）
│   ├── app/
│   │   ├── main.py     # 应用入口
│   │   ├── models.py   # SQLAlchemy 2.0 异步 ORM（8 张表）
│   │   ├── schemas.py  # Pydantic 模型
│   │   ├── routers/    # 17 个路由模块、45 个接口（auth/plan/trip/template/chat/kb/map/ocr/ota/ticket/membership/distribution/collection/service/sms/track/user）
│   │   ├── services/   # 业务逻辑：行程生成/限流/认证/模板/对话/天气/支付
│   │   ├── ai/         # LLM 封装（无 Key 时回退本地生成器）
│   │   └── utils/      # JWT / 微信
│   ├── kb/             # RAG 知识层：语料 / embedding / 索引构建 / Milvus 向量检索 / 景点候选校验
│   ├── scripts/        # build_kb.py（索引/缓存重建 CLI）、check_schema.py（schema 体检）
│   │   ├── dev/        # ticket_mcp_stub.py（12306-mcp 开发替身，不在产品链路）
│   │   ├── migrations/ # 幂等增量迁移（create_all 不会给旧表加约束）
│   │   └── legacy/     # tests_offline.py（历史离线验证脚本）
│   ├── tests/          # 170 例 pytest，强制离线（临时 SQLite、外部 API 全 mock）
│   ├── requirements.txt
│   └── .env.example
├── gateway/            # Nginx 反向代理（Dockerfile + nginx.conf）
├── docker-compose.yml  # mysql:8.0 + redis:7 + backend + gateway
├── docs/               # 产品与技术方案文档（0-立项 ~ 11-开发记录，含 API 文档、部署指南、上架指南）
└── outputs/            # 图标产出、设计稿预览 HTML 与生成脚本
```

---

## 一、前端运行（需后端）

前端**没有 mock 模式**：`miniprogram/utils/mock.js` 已删除，所有页面一律请求真实后端
（此前 mock 的响应结构和后端逐渐漂移，收藏页、行程时间戳、VIP 字段都因此出错）。
启动顺序：先把后端跑起来，再导入前端。

1. 启动后端（见下一节），确认 `http://127.0.0.1:8000/api/health` 返回 `{"status":"ok"}`
2. 安装[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
3. 「导入项目」→ 选择 `miniprogram/` 目录
4. AppID 填 `miniprogram/config/env.js` 里的 `WX_APP_ID`（真机跳转第三方小程序必须用真实 AppID，测试号不行）
5. 「详情 → 本地设置」勾选「不校验合法域名」（开发阶段）
6. 编译后即可在模拟器/真机预览：登录 → 首页 → 表单规划 → 行程详情 → 保存 → 我的行程

> `pages/` 下 22 个页面均已接入真实接口（无占位空页）。
> 城市列表在 `miniprogram/utils/cities.js`（产品数据，不再住在 mock 里）。

---

## 二、后端运行

```bash
cd server
python -m venv venv
venv\Scripts\pip install -r requirements.txt   # macOS/Linux: source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env                            # 按需填写微信/LLM/数据库配置
venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- 本地默认 SQLite（`sqlite+aiosqlite:///./banyou.db`），首次启动自动建表并写入示例模板数据；容器部署由 compose 注入 MySQL 8.0（`mysql+aiomysql://`）。
- 配置了 `LLM_API_KEY` 时行程生成会调用真实大模型；未配置则使用内置本地生成器。景点事实来自 RAG 知识层：**9 城手工语料 129 条 + 高德 POI 候选池 264 条 = 索引 393 条 / 覆盖 21 城**（见下文「知识检索层」）。
- 启动后访问 `http://127.0.0.1:8000/` 可见 `{ "code": 0, "message": "知途 AI 旅行 API 运行中", "data": null }`，`GET /api/health` 返回 `{ "status": "ok" }`。
- `/docs`、`/redoc`、`/openapi.json` 已在 `app/main.py` 显式关闭（上线安全加固）；接口清单看 `docs/6-API接口文档.md` 第十节，本地调试需要 Swagger 时临时把这三个参数改回默认。

---

## 三、前后端联调

1. `miniprogram/config/env.js` 中把 `BASE_URL` 指向后端：
   - 模拟器：`http://127.0.0.1:8000`
   - 真机：填电脑局域网 IP（如 `http://192.168.10.8:8000`，手机与电脑同一路由器）。
     注意 IP 末尾**不带 `/api`**，前端各接口自带 `/api` 前缀
   - 上线：必须 HTTPS 公网域名，并在公众平台「开发设置 → 服务器域名 → request 合法域名」添加
2. `miniprogram/project.config.json` 已设 `urlCheck: false`，开发阶段不校验域名。
3. 微信开发者工具中编译，前端即请求本地后端。

> 生产环境安全约束：`APP_ENV=production` 时若 `JWT_SECRET` 仍是默认开发值，后端会**拒绝启动**；
> 短信服务未配置 key 也会直接报错，不会把验证码回传给前端。

---

## 四、核心接口一览

后端共 **45 个业务接口**（17 个路由模块，命名统一 `/api/模块/动作`，返回 `{code, msg, data}`）+ `/`、`/api/health` 两个探活接口，完整清单见 `docs/6-API接口文档.md` 第十节。核心链路：

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| POST | `/api/auth/login` | 微信 code 换 token（未配 AppID 时返回本地 openid） |
| POST | `/api/plan/form` | 表单规划生成行程（受每日限流） |
| POST | `/api/plan/quick` | 一句话快规划 |
| POST | `/api/plan/chat-adjust` | 对话微调行程 |
| GET  | `/api/trip/list` | 我的行程列表（status: active/all） |
| POST | `/api/trip/save` | 保存行程 |
| POST | `/api/trip/delete` | 删除行程 |
| GET  | `/api/template/hot` | 精选模板列表 |
| POST | `/api/template/use` | 模板加载为行程 |
| POST | `/api/chat/qa` | 旅游智能问答（先检索，检索为空直接拒答） |
| POST | `/api/chat/luggage` | 行李清单 |
| POST | `/api/chat/food` | 美食红黑榜 |
| GET  | `/api/kb/status` | 索引是否已建、文档数与城市覆盖 |
| GET  | `/api/kb/search` | 只读检索调试接口 |
| GET  | `/api/membership/plans` | 会员套餐 |
| POST | `/api/membership/order` | 创建支付订单 |

---

## 五、知识检索层（RAG）

行程生成与问答的事实来源，不是「把裸问题丢给大模型」：

| 模块 | 文件 | 职责 |
| :--- | :--- | :--- |
| 语料 | `server/kb/corpus/city_spots.json` | 9 城手工景点语料（129 条文档） |
| 候选池 | `server/kb/candidates.py` | 语料 + 高德 POI 合成可排入行程的景点名单，按城市缓存 30 分钟 |
| 向量化 | `server/kb/embedder.py` | 阿里云百炼 `text-embedding-v3`，dim 1024，带本地 embedding 缓存 |
| 索引 | `server/kb/index_builder.py` | 语料 + 各城市 POI 一起索引 → 393 条 / 21 城 |
| 检索 | `server/kb/retriever.py` | city 硬过滤下推成 Milvus filter → 向量 top-k → 分数/实体双闸门；Milvus 连不上或 embedding 失败时降级关键词 |

**向量存储：Milvus（自建 milvus-lite 容器）**。393 条这个量级，进程内点积本来只要 1 ms，迁 Milvus 不是为了性能，是为了把 metadata 过滤和语料增量重建交给正经的向量存储。代价全部实测：召回与迁移前逐条一致（17 个真实提问，分数偏差 <1e-4），检索 p50 从 1.1 ms 涨到 3.5 ms（容器 TCP 形态约 28 ms，8 路并发实测会排队到 350 ms），后端 import 多 89 MB（pymilvus），另加一个 147 MB 的向量库容器。没上官方 Milvus Standalone 是因为它要连带 etcd + MinIO 约 3 GB，这台 2 GB 机器放不下；milvus-lite 官方自我定位是 local development/testing，不是集群方案，换官方镜像只改 compose。存储封在 `retriever.py` 一个文件里，调用方不动。语料的竞争者不是向量库，而是持续扩城市的真实内容。

两个坑记在这儿：**①** `city` 是用户可控入参，milvus-lite 不支持参数化 filter（`filter_template_values` 实测报错），filter 里的字符串必须转义，否则 `杭州" or city == "北京` 能同时命中两城、绕过城市硬过滤；**②** `MILVUS_URI` 这个环境变量被 pymilvus 在 import 时自己读走并要求 http 形式，所以本项目用 `KB_MILVUS_URI`。

**判据是双条件**：分数过线（有城市过滤时 `MIN_SCORE=0.55`，无城市时 `0.65`）**且**（≥`STRONG_SCORE` 0.65 或景点名出现在问题里）。实测「问灵隐寺要不要预约」的语义近邻第二名是北京故宫——串味发生在语义层面、调阈值调不掉，所以 city 硬过滤必须在打分之前。

**部署后必须手动重建索引**：`docker compose up -d --build`（现在会多起一个 `milvus` 容器）→ `docker compose exec backend python scripts/build_kb.py` → 在 backend 容器内确认：`python -c "from kb.retriever import retriever as r; print(r.status())"`，要看到 `indexed: true` 且 `engine: milvus`（`/api/kb/status` 也可查，但要带 Bearer token）。向量集合落在 `milvus_data` 命名卷里、不进镜像；`server/.dockerignore` 同时排除本地内嵌库 `kb/corpus/milvus.db*` 和旧 flat 产物（`index.vec` / `index.meta.json` / `embed_cache.json`），防止构建机残留被 `COPY . .` 烤进镜像、静默带着过期语料上线。`build_kb.py` 走 `KB_MILVUS_URI` 把向量写进 Milvus 服务（milvus-lite 对数据目录加锁，不能让第二个进程直接开文件），所以 backend 必须能通到 `milvus:19530`；它会打真实 HTTP，需要 `GAODE_WEB_KEY`（POI）与 `VISION_API_KEY`（embedding，同一把百炼 key 即可，`EMBEDDING_API_*` 留空）。

### 常用运维脚本

| 命令 | 用途 |
| :--- | :--- |
| `python db_init.py` | 建全部表 + 写模板种子（幂等；SQLite 零配置可跑） |
| `python scripts/check_schema.py` | **schema 体检**：对比模型与库结构，报缺表/缺列/缺唯一索引。`create_all` 不会给旧表加约束，历史上 `invite_code`、`collections` 唯一索引都因此漂移过 |
| `python scripts/build_kb.py --status` | 索引/缓存/凭据体检，退出码非 0 表示待处理 |
| `python scripts/build_kb.py --rebuild-embed-cache` | **只重建 embedding 缓存**（不重新拉 POI、不动索引文件）。`embed_cache.json` 不受版本控制，误删后靠它几分钟恢复 |
| `python scripts/migrations/001_collection_unique.py` | 幂等补 `collections` 唯一索引（先删重复再加约束） |

### 生产环境硬约束（启动时校验，不满足直接拒绝启动）

`APP_ENV=production` 时必须配置：
1. `JWT_SECRET` ≥32 位随机串（不能是默认开发值）
2. `REDIS_URL` —— 每日限流、短信验证码、发送频率限制、微信 access_token 缓存都依赖它；
   缺了会**静默降级成进程内计数**，多 worker 下额度直接翻倍

另外生产态若短信服务未配置 key，`/api/sms/send` 会直接报错而不是把验证码回传前端。

---

## 六、测试

`server/tests/` 共 **170 例**（12 个文件），全部强制离线：临时 SQLite 建库、外部 API（高德/百炼/微信）一律 mock，不碰共享演示库。覆盖检索与拒答、候选池校验、天气覆盖、内容安全、CORS 策略、依赖完整性与路由注册；`tests/test_regressions.py` 是 2026-10-23 代码审查的回归用例（注销失效、验证码爆破、收藏字段、时间戳单位、积分并发等）。

```bash
cd server
venv\Scripts\python -m pytest -q        # macOS/Linux: python -m pytest -q
```

---

## 七、上线路径（简述）

1. 注册微信小程序账号（**企业/个体户主体**，否则无支付与 OCR 权限）
2. 后端部署到云服务器（`docker compose`：mysql + redis + milvus + backend + gateway 五个服务），详见 `docs/知途AI Docker部署指南.md`
3. **部署后重建 RAG 索引**（第 2 步不做这步，检索会静默降级成关键词模式）
4. 在公众平台配置 request 合法域名（HTTPS）→ 前端 `env.js` 把 `BASE_URL` 改成正式域名
5. 微信开发者工具「上传」代码 → 公众平台提交审核 → 发布
6. 详细合规要点见 `docs/8-小程序UI落地规范.md` 第八节

---

## 八、品牌

- 产品名：**知途 AI 旅行** ——「智慧规划，伴你旅途」
- 主色 `#4A90D9`，辅助橙 `#FF6B35`，会员金 `#D4A951`，小众紫 `#722ED1`
- 设计规范见 `docs/8-小程序UI落地规范.md`，图标与设计稿预览产出见 `outputs/`

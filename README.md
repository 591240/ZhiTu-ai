# 知途 AI 旅行 · AI 智能短途行程规划小程序

> 面向 1-4 天短途自由行用户的 AI 行程规划工具：四种创建方式（表单 / 一句话 / 截图 / 手动）、大众+小众双路线、旅游智能问答、第三方服务快捷跳转。
> 产品原名「智随伴游」（曾用名「伴游」），现已统一更名为 **知途 AI 旅行**。

---

## 项目结构

```
知途 AI 旅行/
├── miniprogram/        # 微信原生小程序前端（WXML/WXSS/JS）
│   ├── pages/          # 14 个页面（首页/登录/表单/一句话/详情/行程/对话/模板/会员/...）
│   ├── components/     # 自定义组件（route-tag 等）
│   ├── utils/          # request / storage / mock / auth / format
│   ├── config/env.js   # 环境配置：USE_MOCK、BASE_URL、品牌名
│   └── app.json        # 全局配置 + tabBar（首页/我的行程/我的）
├── server/             # FastAPI 后端（Python 3.13+）
│   ├── app/
│   │   ├── main.py     # 应用入口
│   │   ├── models.py   # ORM 模型（8 张表）
│   │   ├── schemas.py  # Pydantic 模型
│   │   ├── routers/    # 路由：auth/plan/trip/template/chat/service/membership/collection
│   │   ├── services/   # 业务逻辑：行程生成/限流/认证/模板/对话/支付
│   │   ├── ai/         # LLM 封装（无 Key 时回退本地生成器）
│   │   └── utils/      # JWT / 微信
│   ├── requirements.txt
│   └── .env.example
├── docs/               # 产品与技术方案文档（0-立项 ~ 8-UI落地规范 + 9-开发运行指南）
└── UI导出/             # Ardot 设计稿导出的 12 页 PNG + 合并 PDF
```

---

## 一、前端预览（零后端，立即可看）

前端默认 `USE_MOCK=true`，内置示例数据，无需后端即可在微信开发者工具中预览全部已实现的页面。

1. 安装[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 「导入项目」→ 选择 `miniprogram/` 目录
3. AppID 选「测试号」（项目已配 `touristappid`，可直接预览）
4. 编译后即可在模拟器/真机预览：登录 → 首页 → 表单规划 → 行程详情 → 保存 → 我的行程

> 已实现页面：登录、首页、AI 表单规划、行程详情、我的行程、个人中心；其余页面（一句话/截图/手动/对话/模板/会员/收藏/发布/设置）已建占位，可继续填充。

---

## 二、后端运行

```bash
cd server
python -m venv venv
venv\Scripts\pip install -r requirements.txt   # macOS/Linux: source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env                            # 按需填写微信/LLM/数据库配置
venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- 默认使用 SQLite（`sqlite+aiosqlite:///./banyou.db`），首次启动自动建表并写入示例模板数据。
- 配置了 `LLM_API_KEY` 时行程生成会调用真实大模型；未配置则使用内置示例生成器（杭州/成都已有景点库，其他城市走通用模板）。
- 启动后访问 `http://127.0.0.1:8000/` 可见 `{ "message": "知途 AI 旅行 API 运行中" }`，接口文档 `http://127.0.0.1:8000/docs`。

---

## 三、前后端联调

1. `miniprogram/config/env.js` 中：
   - `USE_MOCK = false`
   - `BASE_URL = 'http://127.0.0.1:8000/api'`（真机调试需 HTTPS + 公众号配置合法域名；模拟器/本地直连即可）
2. `miniprogram/project.config.json` 已设 `urlCheck: false`，开发阶段不校验域名。
3. 微信开发者工具中编译，前端即请求本地后端。

---

## 四、核心接口一览

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| POST | `/api/auth/login` | 微信 code 换 token（无 AppID 返回 mock） |
| POST | `/api/plan/form` | 表单规划生成行程（受每日限流） |
| POST | `/api/plan/quick` | 一句话快规划 |
| POST | `/api/plan/chat-adjust` | 对话微调行程 |
| GET  | `/api/trip/list` | 我的行程列表（status: active/all） |
| POST | `/api/trip/save` | 保存行程 |
| POST | `/api/trip/delete` | 删除行程 |
| GET  | `/api/template/hot` | 精选模板列表 |
| POST | `/api/template/use` | 模板加载为行程 |
| POST | `/api/chat/qa` | 旅游智能问答 |
| POST | `/api/chat/luggage` | 行李清单 |
| POST | `/api/chat/food` | 美食红黑榜 |
| GET  | `/api/membership/plans` | 会员套餐 |
| POST | `/api/membership/order` | 创建支付订单 |

---

## 五、上线路径（简述）

1. 注册微信小程序账号（**企业/个体户主体**，否则无支付与 OCR 权限）
2. 后端部署到云服务器（Docker + Nginx + HTTPS），在公众平台配置 request 合法域名
3. 微信开发者工具「上传」代码 → 公众平台提交审核 → 发布
4. 详细合规要点见 `docs/8-小程序UI落地规范.md` 第八节

---

## 六、品牌

- 产品名：**知途 AI 旅行** ——「智慧规划，伴你旅途」
- 主色 `#4A90D9`，辅助橙 `#FF6B35`，会员金 `#D4A951`，小众紫 `#722ED1`
- 设计规范见 `docs/8-小程序UI落地规范.md` 与 `UI导出/`

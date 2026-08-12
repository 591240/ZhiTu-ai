# 知途 AI 旅行 —— MVP 技术实现方案

| 项目     | 内容                |
| :------- | :------------------ |
| 文档名称 | MVP 技术实现方案     |
| 版本     | V1.0                |
| 编制时间 | 2026 年 08 月 06 日 |
| 开发模式 | 单人开发 + AI 辅助   |
| 目标周期 | 3 天核心 Demo + 4 天完整迭代 |

---

## 一、技术选型总览

| 技术层     | 选型                          | 选型理由                                              |
| :--------- | :---------------------------- | :---------------------------------------------------- |
| 前端       | 微信原生小程序 (WXML/WXSS/JS) | 原生性能最佳，无需额外框架学习成本；与微信生态深度集成   |
| UI 组件库  | Vant Weapp                    | 轻量级、组件丰富、文档完善、社区活跃                     |
| 后端框架   | Python FastAPI                | 异步高性能、自动生成 OpenAPI 文档、Pydantic 数据校验     |
| 数据库     | MySQL 8.0                     | 成熟稳定、支持 JSON 字段、单机性能足够                    |
| 缓存       | Redis 7.0                     | 限流计数、模板缓存、LLM 结果缓存、降低 AI 调用成本        |
| ORM        | SQLAlchemy 2.0 + PyMySQL      | 成熟 ORM、支持异步、参数化查询防注入                     |
| AI - LLM   | 通义千问 / DeepSeek API        | 中文理解能力强、API 兼容 OpenAI 格式、成本低              |
| AI - OCR   | 百度 OCR / 腾讯 OCR            | 中文识别准确率高、有免费额度                              |
| 部署       | Docker + Nginx                | 容器化部署简单、Nginx 反向代理 + HTTPS                    |
| 服务器     | 阿里云/腾讯云 2核4G            | 满足冷启动阶段需求、月费 90 元                            |

---

## 二、项目结构设计

### 2.1 后端项目结构

```
zhisuibanyou-api/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── config.py                  # 配置管理 (环境变量)
│   ├── database.py                # 数据库连接 & Session
│   ├── redis_client.py            # Redis 连接
│   ├── dependencies.py            # 依赖注入 (Token认证/限流)
│   │
│   ├── models/                    # 数据模型 (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── trip.py
│   │   ├── template.py
│   │   ├── collection.py
│   │   ├── order.py
│   │   ├── chat_history.py
│   │   ├── city.py
│   │   └── service_link.py
│   │
│   ├── schemas/                   # 请求/响应模型 (Pydantic)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── trip.py
│   │   ├── template.py
│   │   ├── chat.py
│   │   ├── order.py
│   │   └── common.py
│   │
│   ├── api/                       # 路由层
│   │   ├── __init__.py
│   │   ├── router.py              # 路由聚合
│   │   ├── auth.py                # 认证模块
│   │   ├── plan.py                # 行程规划模块
│   │   ├── trip.py                # 行程管理模块
│   │   ├── template.py            # 模板模块
│   │   ├── chat.py                # 对话模块
│   │   ├── service.py             # 服务跳转模块
│   │   ├── collection.py          # 收藏模块
│   │   ├── membership.py          # 会员模块
│   │   └── order.py               # 订单模块
│   │
│   ├── services/                  # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_service.py        # 微信登录逻辑
│   │   ├── plan_service.py        # 行程生成逻辑
│   │   ├── trip_service.py        # 行程 CRUD 逻辑
│   │   ├── template_service.py    # 模板逻辑
│   │   ├── chat_service.py        # 对话逻辑
│   │   ├── quota_service.py       # 限流逻辑
│   │   └── payment_service.py     # 支付逻辑
│   │
│   ├── ai/                        # AI 能力层
│   │   ├── __init__.py
│   │   ├── llm_client.py          # LLM API 封装
│   │   ├── ocr_client.py          # OCR API 封装
│   │   └── prompts/               # Prompt 模板
│   │       ├── __init__.py
│   │       ├── form_plan.py       # 表单规划提示词
│   │       ├── quick_plan.py      # 一句话规划提示词
│   │       ├── ocr_plan.py        # 截图识别提示词
│   │       ├── adjust_plan.py     # 对话微调提示词
│   │       └── qa.py              # 旅游问答提示词
│   │
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       ├── jwt_utils.py           # JWT 生成/验证
│       ├── wechat.py              # 微信 API 封装
│       └── cache.py               # 缓存装饰器
│
├── alembic/                       # 数据库迁移
│   └── versions/
├── tests/                         # 测试
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env
```

### 2.2 前端项目结构

```
zhisuibanyou-mini/
├── miniprogram/
│   ├── app.js                     # 小程序入口
│   ├── app.json                   # 全局配置
│   ├── app.wxss                   # 全局样式
│   │
│   ├── pages/                     # 页面
│   │   ├── index/                 # 首页
│   │   │   ├── index.wxml
│   │   │   ├── index.wxss
│   │   │   └── index.js
│   │   ├── plan-form/             # 表单规划
│   │   ├── plan-quick/            # 一句话规划
│   │   ├── plan-ocr/              # 截图识别
│   │   ├── plan-manual/           # 手动编排
│   │   ├── trip-detail/           # 行程详情
│   │   ├── trip-list/             # 行程列表
│   │   ├── chat/                  # 对话助手
│   │   ├── mine/                  # 个人中心
│   │   ├── vip/                   # 会员中心
│   │   ├── template-detail/       # 模板详情
│   │   ├── collection/            # 我的收藏
│   │   ├── published/             # 我的发布
│   │   ├── settings/              # 系统设置
│   │   └── login/                 # 登录授权
│   │
│   ├── components/                # 自定义组件
│   │   ├── trip-card/             # 行程卡片
│   │   ├── spot-card/             # 景点卡片
│   │   ├── meal-card/             # 餐饮卡片
│   │   ├── template-card/         # 模板卡片
│   │   ├── service-grid/          # 服务网格
│   │   ├── chat-bubble/           # 对话气泡
│   │   ├── loading/               # 加载动画
│   │   └── empty-state/           # 空状态
│   │
│   ├── utils/                     # 工具函数
│   │   ├── request.js             # 网络请求封装
│   │   ├── auth.js                # 认证工具
│   │   ├── storage.js             # 本地存储
│   │   └── format.js              # 格式化工具
│   │
│   ├── config/                    # 配置
│   │   └── env.js                 # 环境配置
│   │
│   └── assets/                    # 静态资源
│       ├── icons/
│       └── images/
│
├── project.config.json
└── sitemap.json
```

---

## 三、核心技术实现方案

### 3.1 微信授权登录

**实现流程：**

```python
# app/services/auth_service.py

import httpx
from app.config import settings

class AuthService:
    async def wechat_login(self, code: str, nickname: str = None, avatar_url: str = None):
        """微信登录：code → openid → JWT"""
        # 1. 调用微信 API 获取 openid
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": settings.WX_APP_ID,
                    "secret": settings.WX_APP_SECRET,
                    "js_code": code,
                    "grant_type": "authorization_code"
                }
            )
            data = resp.json()

        openid = data.get("openid")
        if not openid:
            raise Exception("微信登录失败: 未获取到 openid")

        # 2. 查询或创建用户
        user = await self.get_or_create_user(openid, nickname, avatar_url)

        # 3. 生成 JWT Token
        token = create_jwt_token({"user_id": user.id, "openid": openid})

        return token, user
```

**前端调用：**

```javascript
// miniprogram/utils/auth.js

async function login() {
    // 1. 调用 wx.login 获取 code
    const { code } = await wx.login()

    // 2. 调用后端登录接口
    const res = await request({
        url: '/api/auth/login',
        method: 'POST',
        data: { code }
    })

    // 3. 存储 token
    wx.setStorageSync('token', res.data.token)
    wx.setStorageSync('userInfo', res.data.user)

    return res.data
}
```

### 3.2 LLM 行程生成（核心）

**Prompt 工程设计：**

```python
# app/ai/prompts/form_plan.py

FORM_PLAN_PROMPT = """你是一个专业的旅游行程规划师。请根据以下用户需求，生成一份结构化的分日行程。

## 用户需求
- 目的地：{city}
- 出行天数：{days}天
- 出行人群：{crowd_type}
- 预算档位：{budget_level}
- 游玩偏好：{preferences}
- 交通方式：{transport_mode}
- 路线风格：{route_type}
- 特殊备注：{remark}

## 路线风格说明
{route_style_desc}

## 输出要求
请严格按照以下 JSON 格式输出，不要包含任何其他文字：

```json
{{
    "title": "行程标题",
    "itinerary": [
        {{
            "day_number": 1,
            "date_label": "第一天",
            "spots": [
                {{
                    "name": "景点名称",
                    "address": "详细地址",
                    "time_slot": "morning/afternoon/evening",
                    "duration_min": 180,
                    "ticket_price": 0,
                    "category": "自然风光/人文历史/美食/亲子/网红打卡",
                    "description": "游玩描述和注意事项"
                }}
            ],
            "meals": [
                {{
                    "name": "餐厅名称",
                    "type": "breakfast/lunch/dinner",
                    "avg_price": 100,
                    "specialty": "特色菜品",
                    "address": "餐厅地址"
                }}
            ],
            "transport": [
                {{
                    "from": "起点",
                    "to": "终点",
                    "mode": "步行/公交/地铁/打车",
                    "duration_min": 30,
                    "cost": 5
                }}
            ],
            "budget": 500.00,
            "tips": "当日避坑提示，用换行分隔多条"
        }}
    ],
    "total_budget": 1000.00
}}
```

## 约束条件
1. 景点必须是真实存在的，地址必须准确
2. {route_type}路线应{route_style_constraint}
3. 餐饮推荐本地特色，价格符合{budget_level}预算
4. 每日景点数量合理（2-4个），避免行程过满
5. 交通方式优先{transport_mode}
6. 门票价格必须为实际价格，免费为0
"""
```

**LLM 调用封装：**

```python
# app/ai/llm_client.py

import httpx
import json
from app.config import settings

class LLMClient:
    def __init__(self):
        self.api_url = settings.LLM_API_URL
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    async def generate(self, prompt: str, temperature: float = 0.7) -> dict:
        """调用 LLM 生成结构化行程"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.api_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是专业旅游行程规划师，只输出JSON格式结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "response_format": {"type": "json_object"}
                }
            )
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            # 解析 JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # 尝试从 markdown 代码块中提取
                import re
                match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                raise Exception("LLM 返回格式异常")

    async def generate_stream(self, prompt: str):
        """流式生成（用于对话问答）"""
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.api_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是旅游智能助手，回答简洁实用。"},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": True
                }
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
```

### 3.3 Redis 限流方案

```python
# app/services/quota_service.py

from app.redis_client import redis
from datetime import datetime, timedelta

class QuotaService:
    DAILY_LIMIT = 3  # 免费用户每日限制

    async def check_and_consume(self, user_id: int, is_vip: bool) -> bool:
        """检查并消耗一次生成次数"""
        if is_vip:
            return True  # 会员不限次数

        today = datetime.now().strftime("%Y%m%d")
        key = f"user:daily_count:{user_id}:{today}"

        # 原子操作：获取当前值
        current = await redis.get(key)
        current = int(current) if current else 0

        if current >= self.DAILY_LIMIT:
            return False  # 次数用尽

        # 原子递增
        new_count = await redis.incr(key)

        # 首次设置过期时间（到当日24点）
        if new_count == 1:
            expire_seconds = int(
                (datetime.now().replace(hour=23, minute=59, second=59) - datetime.now()
            ).total_seconds())
            await redis.expire(key, expire_seconds)

        return True

    async def get_remaining(self, user_id: int, is_vip: bool) -> int:
        """获取剩余次数"""
        if is_vip:
            return -1  # 不限

        today = datetime.now().strftime("%Y%m%d")
        key = f"user:daily_count:{user_id}:{today}"
        current = await redis.get(key)
        current = int(current) if current else 0
        return max(0, self.DAILY_LIMIT - current)
```

### 3.4 LLM 结果缓存

```python
# app/utils/cache.py

import hashlib
import json
from app.redis_client import redis

async def get_llm_cache(prompt: str) -> dict | None:
    """获取 LLM 缓存结果"""
    key = f"llm:cache:{hashlib.md5(prompt.encode()).hexdigest()}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    return None

async def set_llm_cache(prompt: str, result: dict, ttl: int = 604800):
    """设置 LLM 缓存（7天）"""
    key = f"llm:cache:{hashlib.md5(prompt.encode()).hexdigest()}"
    await redis.set(key, json.dumps(result, ensure_ascii=False), ex=ttl)
```

### 3.5 OCR 截图识别

```python
# app/ai/ocr_client.py

import httpx
import base64
from app.config import settings

class OCRClient:
    def __init__(self):
        self.api_key = settings.OCR_API_KEY
        self.secret_key = settings.OCR_SECRET_KEY

    async def recognize(self, image_bytes: bytes) -> str:
        """识别图片中的文字"""
        image_b64 = base64.b64encode(image_bytes).decode()

        async with httpx.AsyncClient(timeout=15) as client:
            # 获取 access_token (实际应缓存)
            token_resp = await client.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.secret_key
                }
            )
            access_token = token_resp.json()["access_token"]

            # 调用通用文字识别
            resp = await client.post(
                "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic",
                params={"access_token": access_token},
                data={
                    "image": image_b64,
                    "language_type": "CHN_ENG"
                }
            )

            result = resp.json()
            words = [item["words"] for item in result.get("words_result", [])]
            return "\n".join(words)
```

### 3.6 微信支付实现

```python
# app/services/payment_service.py

import hashlib
import time
from app.config import settings

class PaymentService:
    PLAN_PRICES = {
        "monthly": 19.90,
        "yearly": 129.00
    }

    async def create_order(self, user_id: int, plan_type: str) -> dict:
        """创建支付订单"""
        amount = self.PLAN_PRICES[plan_type]
        order_no = f"ZSBY{int(time.time())}{user_id:06d}"

        # 1. 保存订单到数据库
        order = await self.save_order(user_id, order_no, plan_type, amount)

        # 2. 调用微信统一下单 API
        pay_params = await self.unified_order(order_no, amount)

        return {
            "order_id": order.id,
            "order_no": order_no,
            "amount": amount,
            "pay_params": pay_params
        }

    async def unified_order(self, order_no: str, amount: float) -> dict:
        """微信统一下单"""
        # 调用微信支付 V3 API
        # 返回前端支付所需参数
        pass

    async def handle_callback(self, notify_data: dict) -> bool:
        """处理支付回调"""
        # 1. 验证签名
        # 2. 更新订单状态
        # 3. 更新用户会员状态
        # 4. 创建会员记录
        pass
```

### 3.7 前端网络请求封装

```javascript
// miniprogram/utils/request.js

const BASE_URL = 'https://api.zhisuibanyou.com/api'

function request(options) {
    return new Promise((resolve, reject) => {
        const token = wx.getStorageSync('token')

        wx.request({
            url: BASE_URL + options.url,
            method: options.method || 'GET',
            data: options.data,
            header: {
                'Content-Type': 'application/json',
                'Authorization': token ? `Bearer ${token}` : ''
            },
            success(res) {
                if (res.statusCode === 401) {
                    // Token 过期，重新登录
                    wx.removeStorageSync('token')
                    wx.redirectTo({ url: '/pages/login/login' })
                    reject(new Error('未登录'))
                    return
                }
                if (res.data.code === 0) {
                    resolve(res.data)
                } else {
                    // 业务错误
                    wx.showToast({
                        title: res.data.message,
                        icon: 'none'
                    })
                    reject(res.data)
                }
            },
            fail(err) {
                wx.showToast({
                    title: '网络异常，请重试',
                    icon: 'none'
                })
                reject(err)
            }
        })
    })
}

// 流式请求 (用于对话)
function streamRequest(url, data, onChunk) {
    const token = wx.getStorageSync('token')
    const task = wx.request({
        url: BASE_URL + url,
        method: 'POST',
        data,
        header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'Accept': 'text/event-stream'
        },
        enableChunked: true,
        responseType: 'text',
        success(res) {
            // 处理流式数据
        }
    })

    // 监听数据分块
    task.onChunkReceived((res) => {
        const text = new TextDecoder('utf-8').decode(res.data)
        onChunk(text)
    })

    return task
}

module.exports = { request, streamRequest }
```

---

## 四、数据库初始化方案

### 4.1 Alembic 迁移配置

```python
# alembic/env.py

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from app.database import Base
from app.models import *  # 导入所有模型

# 配置异步引擎
engine = async_engine_from_config(
    config.get_section(config.config_ini_section),
    prefix="sqlalchemy."
)

# 自动检测模型变化
target_metadata = Base.metadata
```

### 4.2 城市初始数据

```python
# scripts/init_cities.py

CITIES = [
    {"name": "杭州", "province": "浙江", "pinyin": "hangzhou", "is_hot": True},
    {"name": "成都", "province": "四川", "pinyin": "chengdu", "is_hot": True},
    {"name": "西安", "province": "陕西", "pinyin": "xian", "is_hot": True},
    {"name": "苏州", "province": "江苏", "pinyin": "suzhou", "is_hot": True},
    {"name": "南京", "province": "江苏", "pinyin": "nanjing", "is_hot": True},
    {"name": "厦门", "province": "福建", "pinyin": "xiamen", "is_hot": True},
    {"name": "重庆", "province": "重庆", "pinyin": "chongqing", "is_hot": True},
    {"name": "长沙", "province": "湖南", "pinyin": "changsha", "is_hot": True},
    {"name": "武汉", "province": "湖北", "pinyin": "wuhan", "is_hot": True},
    {"name": "青岛", "province": "山东", "pinyin": "qingdao", "is_hot": True},
]
```

---

## 五、Docker 部署方案

### 5.1 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 5.2 docker-compose.yml

```yaml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@db:3306/zhisuibanyou
      - REDIS_URL=redis://redis:6379/0
      - WX_APP_ID=${WX_APP_ID}
      - WX_APP_SECRET=${WX_APP_SECRET}
      - LLM_API_KEY=${LLM_API_KEY}
      - OCR_API_KEY=${OCR_API_KEY}
      - OCR_SECRET_KEY=${OCR_SECRET_KEY}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - db
      - redis
    restart: always

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=zhisuibanyou
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    restart: always

  redis:
    image: redis:7.0-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: always

volumes:
  mysql_data:
  redis_data:
```

### 5.3 Nginx 配置

```nginx
# nginx.conf
upstream fastapi {
    server app:8000;
}

server {
    listen 443 ssl;
    server_name api.zhisuibanyou.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}

server {
    listen 80;
    server_name api.zhisuibanyou.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 六、环境变量配置

```env
# .env

# 应用配置
APP_ENV=production
APP_DEBUG=false

# 数据库
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/zhisuibanyou

# Redis
REDIS_URL=redis://localhost:6379/0

# 微信小程序
WX_APP_ID=your_app_id
WX_APP_SECRET=your_app_secret

# JWT
JWT_SECRET=your_jwt_secret
JWT_EXPIRE_HOURS=168

# LLM 配置
LLM_API_URL=https://api.deepseek.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=deepseek-chat

# OCR 配置
OCR_API_KEY=your_ocr_api_key
OCR_SECRET_KEY=your_ocr_secret_key

# 微信支付
WX_MCH_ID=your_mch_id
WX_MCH_SERIAL_NO=your_serial_no
WX_MCH_PRIVATE_KEY=your_private_key
WX_API_V3_KEY=your_api_v3_key

# 限流配置
DAILY_PLAN_LIMIT=3

# 缓存
LLM_CACHE_TTL=604800
TEMPLATE_CACHE_TTL=604800
```

---

## 七、MVP 开发排期（3+4 天）

### 7.1 Day 1：后端基础 + 数据库

| 时段  | 任务                              | 产出                              |
| :---- | :-------------------------------- | :-------------------------------- |
| 上午  | 项目搭建、依赖安装、配置管理      | FastAPI 项目可运行                  |
| 上午  | 数据库设计、建表、初始数据         | MySQL 11 张表 + 城市数据            |
| 下午  | 用户认证模块 (登录/Token)          | /api/auth/login 可用               |
| 下午  | 行程 CRUD 接口                    | /api/trip/* 全部可用                |
| 下午  | 模板列表/详情接口                 | /api/template/* 可用               |
| 晚上  | LLM 调用封装 + Prompt 设计         | 行程生成接口核心逻辑跑通             |

### 7.2 Day 2：前端页面 + 接口对接

| 时段  | 任务                              | 产出                              |
| :---- | :-------------------------------- | :-------------------------------- |
| 上午  | 首页、登录页开发                   | 页面可展示，登录可跳转              |
| 上午  | 表单规划页开发                     | 表单可填写并提交                    |
| 下午  | 行程详情页开发                     | 行程可展示分日内容                  |
| 下午  | 行程列表页开发                     | 列表可展示、查看、删除               |
| 下午  | 对话助手页开发                     | 问答可发送和接收                    |
| 晚上  | 个人中心页开发                     | 信息展示 + 功能菜单                 |

### 7.3 Day 3：核心联调 + AI 对接

| 时段  | 任务                              | 产出                              |
| :---- | :-------------------------------- | :-------------------------------- |
| 上午  | 前后端联调：登录→规划→详情→保存    | 核心流程跑通                       |
| 上午  | LLM 行程生成调试（Prompt 调优）    | 行程内容质量达标                    |
| 下午  | 一句话快规划联调                   | 自然语言规划可用                    |
| 下午  | 对话微调联调                       | 行程微调功能可用                    |
| 下午  | 模板广场 + 快捷服务跳转联调        | 模板加载、服务跳转可用               |
| 晚上  | 限流逻辑测试、Bug 修复             | 免费用户 3 次限制生效                |
| 晚上  | **3 天 Demo 可用**                 | **核心功能完整跑通**                |

### 7.4 Day 4-6：完整功能迭代

| 天数  | 任务                              |
| :---- | :-------------------------------- |
| Day 4 | 截图识行程 (OCR + LLM)、手动编排页面 |
| Day 5 | 会员中心 + 微信支付、行程发布功能   |
| Day 6 | 行李清单、美食红黑榜、收藏功能     |

### 7.5 Day 7：测试 + 优化 + 文档

| 时段  | 任务                              |
| :---- | :-------------------------------- |
| 全天  | 全功能联调、Bug 修复、交互优化     |
| 全天  | 录屏、接口文档整理、部署上线       |

---

## 八、性能优化策略

### 8.1 LLM 调用优化

| 策略             | 说明                                              | 预期效果           |
| :--------------- | :------------------------------------------------ | :----------------- |
| Prompt 精简      | 控制 Prompt 长度在 2000 token 以内                  | 降低 30% token 消耗 |
| 结果缓存          | 相同参数请求命中 Redis 缓存                         | 降低 50% LLM 调用  |
| 流式输出          | 问答使用 SSE 流式输出                               | 用户感知等待降低    |
| 超时降级          | LLM 超时返回缓存或提示重试                          | 提升可用性          |
| 大众/小众分离缓存 | 两套 Prompt 独立缓存                                | 缓存命中率提升      |

### 8.2 数据库优化

| 策略           | 说明                                              |
| :------------- | :------------------------------------------------ |
| 索引优化        | 高频查询字段加索引（user_id/city_id/status）         |
| JSON 字段      | 行程内容用 JSON 存储，减少关联查询                   |
| 软删除          | 行程删除用 status=deleted，不做物理删除              |
| 连接池          | SQLAlchemy 连接池配置 (pool_size=10, max_overflow=20)|
| 读写分离(后期)  | 用户量增长后考虑主从分离                             |

### 8.3 缓存策略

| 缓存对象       | Key 格式                        | TTL    | 更新策略           |
| :------------- | :------------------------------ | :----- | :----------------- |
| 城市列表        | city:list                       | 7 天   | 手动刷新            |
| 热门模板列表    | template:hot:list               | 7 天   | 定时刷新            |
| 模板详情        | template:detail:{id}            | 1 天   | 更新时清除          |
| 行程内容        | trip:content:{id}               | 1 小时 | 更新时清除          |
| 服务跳转链接    | service_link:city:{city_id}     | 7 天   | 管理后台更新时清除   |
| LLM 结果        | llm:cache:{md5}                 | 7 天   | 自动过期            |
| 用户当日次数    | user:daily_count:{id}:{date}     | 当日   | 自动过期            |

---

## 九、安全方案

| 安全措施         | 实现方式                                          |
| :--------------- | :------------------------------------------------ |
| JWT Token 认证   | 每次请求校验 Bearer Token，过期自动重新登录          |
| openid 不外泄    | openid 仅存储在后端，前端不接触                      |
| SQL 注入防护     | SQLAlchemy ORM 参数化查询，禁止拼接 SQL              |
| 接口限流         | Redis 实现用户级限流（AI 生成 3 次/天，API 100 次/分）|
| 支付签名校验     | 微信支付 V3 RSA 签名校验                             |
| HTTPS 强制       | Nginx 全站 HTTPS，HTTP 自动跳转 HTTPS                |
| 防重放攻击       | 关键接口加 nonce + timestamp 校验                     |
| 输入校验         | Pydantic 模型校验所有请求参数                         |
| XSS 防护         | 前端输出编码，后端过滤 HTML 标签                      |

---

## 十、监控与日志

### 10.1 日志方案

```python
# app/utils/logger.py

import logging
from app.config import settings

logger = logging.getLogger("zhisuibanyou")
logger.setLevel(logging.INFO)

# 文件日志
file_handler = logging.FileHandler("logs/app.log")
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(file_handler)

# 关键日志记录
# - API 请求日志: method, path, status, duration
# - LLM 调用日志: prompt_length, response_time, token_usage
# - 错误日志: exception traceback
# - 支付日志: order_no, amount, status
```

### 10.2 监控指标

| 指标              | 告警阈值              | 说明                   |
| :---------------- | :-------------------- | :--------------------- |
| API 响应时间      | > 2s                  | 接口性能下降             |
| LLM 调用成功率    | < 95%                  | AI 服务不稳定           |
| LLM 平均响应时间  | > 15s                 | 生成体验差               |
| 服务器 CPU        | > 80%                  | 资源不足                 |
| 服务器内存        | > 85%                  | 资源不足                 |
| MySQL 连接数      | > 80                   | 连接池不足               |
| Redis 内存        | > 80%                  | 缓存不足                 |

# 知途 AI 旅行 —— API 接口文档

| 项目     | 内容                |
| :------- | :------------------ |
| 文档名称 | API 接口文档         |
| 版本     | V1.0                |
| 编制时间 | 2026 年 08 月 06 日 |
| 后端框架 | Python FastAPI      |
| 基础路径 | `https://api.zhisuibanyou.com/api`（**规划中的域名，当前未解析**；本地联调为 `http://127.0.0.1:8000/api`） |
| 文档性质 | 第 1～9 节为**设计态**（2026-08-06 编写，路径风格为 RESTful）；**第 10 节是实现态真值**，由路由代码扫描得到。实现的命名统一为 `/api/模块/动作`，两者路径不可互换 —— 引用接口请以第 10 节为准。 |

---

## 一、通用规范

### 1.1 请求规范

| 项目       | 说明                                                     |
| :--------- | :------------------------------------------------------- |
| 协议       | HTTPS                                                    |
| 数据格式   | JSON (application/json)                                  |
| 字符编码   | UTF-8                                                    |
| 认证方式   | Bearer Token (JWT)，放在 Header `Authorization` 中        |
| 文件上传   | multipart/form-data                                       |
| 时间格式   | ISO 8601 (如 `2026-08-06T18:00:00+08:00`)                |

### 1.2 统一响应格式

**成功响应：**

```json
{
    "code": 0,
    "message": "success",
    "data": { ... }
}
```

**失败响应：**

```json
{
    "code": 1001,
    "message": "参数校验失败",
    "data": null,
    "errors": [
        {
            "field": "days",
            "message": "天数必须在1-4之间"
        }
    ]
}
```

### 1.3 错误码定义

| 错误码 | 说明                   | HTTP 状态码 |
| :----- | :--------------------- | :----------- |
| 0      | 成功                   | 200          |
| 1001   | 参数校验失败           | 422          |
| 1002   | 未登录或 Token 过期    | 401          |
| 1003   | 无权限访问             | 403          |
| 1004   | 资源不存在             | 404          |
| 1005   | 操作冲突               | 409          |
| 2001   | 每日生成次数已用尽     | 429          |
| 2002   | 非会员无法使用此功能   | 403          |
| 2003   | LLM 调用超时           | 504          |
| 2004   | LLM 调用失败           | 502          |
| 2005   | OCR 识别失败           | 502          |
| 3001   | 订单已存在             | 409          |
| 3002   | 支付校验失败           | 400          |
| 5000   | 服务器内部错误         | 500          |

### 1.4 分页规范

**请求参数：**

| 参数     | 类型 | 默认值 | 说明       |
| :------- | :--- | :----- | :--------- |
| page     | int  | 1      | 页码       |
| page_size | int | 20     | 每页条数    |

**响应格式：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [ ... ],
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5
    }
}
```

---

## 二、认证模块

### 2.1 微信登录

**POST** `/auth/login`

用户使用微信授权登录，后端通过 code 换取 openid，返回 JWT Token。

**请求参数：**

| 参数   | 类型   | 必填 | 说明                   |
| :----- | :----- | :--- | :--------------------- |
| code   | string | 是  | wx.login 获取的 code    |
| nickname | string | 否 | 用户昵称                |
| avatar_url | string | 否 | 用户头像 URL           |

**请求示例：**

```json
{
    "code": "0a3xxx...",
    "nickname": "章文彬",
    "avatar_url": "https://wx.qlogo.cn/..."
}
```

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "expires_in": 604800,
        "user": {
            "id": 1,
            "openid": "oXXXXXXXXXXXXX",
            "nickname": "章文彬",
            "avatar_url": "https://wx.qlogo.cn/...",
            "role": "free",
            "vip_expire_time": null,
            "daily_plan_count": 3,
            "created_at": 1761000000000
        }
    }
}
```

---

### 2.2 获取用户信息

**GET** `/user/info`

获取当前登录用户的详细信息。

**请求头：**

```
Authorization: Bearer <token>
```

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "id": 1,
        "nickname": "章文彬",
        "avatar_url": "https://wx.qlogo.cn/...",
        "role": "vip",
        "vip_expire_time": "2026-09-06T18:00:00+08:00",
        "daily_plan_count": -1,
        "stats": {
            "total_trips": 12,
            "total_cities": 8,
            "total_collections": 5,
            "total_published": 3
        }
    }
}
```

> 注：`daily_plan_count` 为 -1 时表示不限次数（会员）

---

### 2.3 更新用户信息

**PUT** `/user/info`

更新用户昵称和头像。

**请求参数：**

| 参数        | 类型   | 必填 | 说明       |
| :---------- | :----- | :--- | :--------- |
| nickname    | string | 否  | 用户昵称    |
| avatar_url  | string | 否  | 头像 URL   |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "id": 1,
        "nickname": "章文彬",
        "avatar_url": "https://wx.qlogo.cn/..."
    }
}
```

---

### 2.4 检查生成次数

**GET** `/user/quota`

获取用户当日剩余 AI 行程生成次数。

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "daily_remaining": 2,
        "daily_limit": 3,
        "is_vip": false,
        "vip_expire_time": null
    }
}
```

---

## 三、行程规划模块

### 3.1 表单规划行程

**POST** `/plan/form`

通过结构化表单参数生成 AI 行程。

**请求头：**

```
Authorization: Bearer <token>
Content-Type: application/json
```

**请求参数：**

| 参数           | 类型     | 必填 | 说明                                          |
| :------------- | :------- | :--- | :-------------------------------------------- |
| city_id        | int      | 是  | 目的地城市 ID                                  |
| days           | int      | 是  | 出行天数 (1-4)                                |
| crowd_type     | string   | 是  | 出行人群: family/couple/student/senior/friend/other |
| budget_level   | string   | 是  | 预算档位: economy/comfort/luxury              |
| preferences    | string[] | 是  | 游玩偏好: nature/culture/food/trending/leisure |
| transport_mode | string   | 否  | 交通方式: self_drive/public/walk/mixed        |
| route_type     | string   | 是  | 路线风格: popular/niche                       |
| remark         | string   | 否  | 特殊备注 (最多 500 字)                         |

**请求示例：**

```json
{
    "city_id": 1,
    "days": 2,
    "crowd_type": "family",
    "budget_level": "comfort",
    "preferences": ["nature", "food"],
    "transport_mode": "public",
    "route_type": "popular",
    "remark": "带5岁小朋友，不要太累"
}
```

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "trip_id": 101,
        "title": "杭州两天亲子游",
        "city": "杭州",
        "days": 2,
        "route_type": "popular",
        "daily_remaining": 2,
        "itinerary": [
            {
                "day_number": 1,
                "date_label": "第一天",
                "spots": [
                    {
                        "name": "西湖",
                        "address": "杭州市西湖区龙井路1号",
                        "time_slot": "morning",
                        "duration_min": 180,
                        "ticket_price": 0,
                        "category": "自然风光",
                        "description": "漫步苏堤，欣赏断桥残雪，适合亲子沿湖散步"
                    },
                    {
                        "name": "雷峰塔",
                        "address": "杭州市西湖区南山路1号",
                        "time_slot": "afternoon",
                        "duration_min": 90,
                        "ticket_price": 40,
                        "category": "人文历史",
                        "description": "登塔远眺西湖全景，了解白蛇传传说"
                    }
                ],
                "meals": [
                    {
                        "name": "楼外楼",
                        "type": "lunch",
                        "avg_price": 120,
                        "specialty": "西湖醋鱼、龙井虾仁",
                        "address": "杭州市西湖区孤山路30号"
                    }
                ],
                "transport": [
                    {
                        "from": "西湖",
                        "to": "雷峰塔",
                        "mode": "步行",
                        "duration_min": 15,
                        "cost": 0
                    }
                ],
                "budget": 280.00,
                "tips": "西湖周末人多，建议早上8点前到达；雷峰塔需提前在公众号预约"
            },
            {
                "day_number": 2,
                "date_label": "第二天",
                "spots": [
                    {
                        "name": "杭州动物园",
                        "address": "杭州市西湖区虎跑路40号",
                        "time_slot": "morning",
                        "duration_min": 150,
                        "ticket_price": 20,
                        "category": "亲子",
                        "description": "适合带小朋友近距离观赏动物"
                    }
                ],
                "meals": [
                    {
                        "name": "知味观",
                        "type": "lunch",
                        "avg_price": 80,
                        "specialty": "小笼包、猫耳朵",
                        "address": "杭州市上城区仁和路83号"
                    }
                ],
                "transport": [
                    {
                        "from": "酒店",
                        "to": "杭州动物园",
                        "mode": "公交",
                        "duration_min": 30,
                        "cost": 4
                    }
                ],
                "budget": 184.00,
                "tips": "动物园建议上午去，动物比较活跃"
            }
        ],
        "total_budget": 464.00
    }
}
```

**错误响应：**

```json
{
    "code": 2001,
    "message": "今日生成次数已用尽，升级会员解锁无限次数",
    "data": null
}
```

---

### 3.2 一句话快规划

**POST** `/plan/quick`

通过自然语言输入生成 AI 行程。

**请求参数：**

| 参数    | 类型   | 必填 | 说明                           |
| :------ | :----- | :--- | :----------------------------- |
| message | string | 是  | 自然语言描述 (10-500 字)        |

**请求示例：**

```json
{
    "message": "下周末想带5岁娃去杭州玩两天，预算800，喜欢自然风景，不要太累"
}
```

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "trip_id": 102,
        "title": "杭州两天亲子自然游",
        "parsed_params": {
            "city": "杭州",
            "days": 2,
            "crowd_type": "family",
            "budget_level": "comfort",
            "preferences": ["nature"],
            "route_type": "popular"
        },
        "itinerary": [ ... ],
        "total_budget": 520.00,
        "daily_remaining": 1
    }
}
```

---

### 3.3 截图识行程

**POST** `/plan/ocr`

上传攻略截图，OCR 识别后由 LLM 转换为结构化行程。**会员功能。**

**请求头：**

```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**请求参数：**

| 参数    | 类型   | 必填 | 说明                          |
| :------ | :----- | :--- | :---------------------------- |
| images  | file[] | 是  | 截图图片 (1-3张, jpg/png, <5MB) |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "trip_id": 103,
        "title": "小红书攻略-杭州三日游",
        "ocr_text": "Day1: 西湖→断桥→白堤→孤山...",
        "itinerary": [ ... ],
        "needs_review": true
    }
}
```

**错误响应：**

```json
{
    "code": 2005,
    "message": "OCR 识别失败，请尝试手动输入文本",
    "data": null
}
```

---

### 3.4 对话微调行程

**POST** `/plan/adjust`

对已有行程进行 AI 对话式微调。

**请求参数：**

| 参数      | 类型   | 必填 | 说明                  |
| :-------- | :----- | :--- | :-------------------- |
| trip_id   | int    | 是  | 行程 ID               |
| message   | string | 是  | 微调指令 (1-500 字)   |

**请求示例：**

```json
{
    "trip_id": 101,
    "message": "把第二天的景点换成西溪湿地，预算减少200"
}
```

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "trip_id": 101,
        "changes": [
            {
                "day": 2,
                "type": "spot_replace",
                "old": "杭州动物园",
                "new": "西溪湿地"
            },
            {
                "type": "budget_change",
                "old": 184.00,
                "new": 120.00
            }
        ],
        "itinerary": [ ... ],
        "total_budget": 400.00
    }
}
```

---

## 四、行程管理模块

### 4.1 获取行程列表

**GET** `/trip/list`

获取当前用户的行程列表。

**请求参数：**

| 参数   | 类型   | 必填 | 默认值 | 说明                                                  |
| :----- | :----- | :--- | :----- | :---------------------------------------------------- |
| status | string | 否   | 无     | `active`=只看使用中；`all`=不过滤；不传同 `all`        |

> ⚠️ 旧实现把 `status=all` 当字面值去比 `trips.status`，导致前端的「全部行程」tab 恒为空。
> 2026-10-23 已修：`all` 与不传都表示不过滤。

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": 101,
                "title": "杭州两天亲子游",
                "city": "杭州",
                "days": 2,
                "route_type": "popular",
                "crowd_type": "family",
                "budget_level": "comfort",
                "status": "active",
                "created_at": 1761000000000,
                "updated_at": 1761000000000
            }
        ],
        "total": 12,
        "page": 1,
        "page_size": 20,
        "total_pages": 1
    }
}
```

---

### 4.2 获取行程详情

**GET** `/trip/{trip_id}`

获取单个行程的完整详情。

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "id": 101,
        "title": "杭州两天亲子游",
        "city": "杭州",
        "days": 2,
        "route_type": "popular",
        "crowd_type": "family",
        "budget_level": "comfort",
        "transport_mode": "public",
        "plan_source": "form",
        "status": "active",
        "created_at": 1761000000000,
        "updated_at": 1761000000000,
        "itinerary": [
            {
                "day_number": 1,
                "date_label": "第一天",
                "spots": [ ... ],
                "meals": [ ... ],
                "transport": [ ... ],
                "budget": 280.00,
                "tips": "西湖周末人多..."
            }
        ],
        "total_budget": 464.00
    }
}
```

---

### 4.3 保存行程

**POST** `/trip`

保存新生成的行程。

**请求参数：**

| 参数           | 类型   | 必填 | 说明                          |
| :------------- | :----- | :--- | :---------------------------- |
| title          | string | 是  | 行程标题                       |
| city_id        | int    | 是  | 城市 ID                        |
| days           | int    | 是  | 天数                           |
| route_type     | string | 是  | 路线风格                        |
| crowd_type     | string | 是  | 人群类型                        |
| budget_level   | string | 是  | 预算档位                        |
| transport_mode | string | 否  | 交通方式                        |
| plan_source    | string | 是  | 来源: form/quick/ocr/manual/template |
| itinerary     | array  | 是  | 行程内容 (同详情格式)            |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "trip_id": 104,
        "created_at": 1761000000000
    }
}
```

---

### 4.4 更新行程

**PUT** `/trip/{trip_id}`

更新已有行程内容。

**请求参数：**

| 参数       | 类型   | 必填 | 说明         |
| :--------- | :----- | :--- | :----------- |
| title      | string | 否  | 行程标题      |
| itinerary  | array  | 否  | 行程内容      |
| status     | string | 否  | 状态          |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "trip_id": 101,
        "updated_at": 1761000000000
    }
}
```

---

### 4.5 删除行程

**DELETE** `/trip/{trip_id}`

删除指定行程（软删除）。

**响应示例：**

```json
{
    "code": 0,
    "message": "行程已删除",
    "data": null
}
```

---

### 4.6 发布行程为模板

**POST** `/trip/{trip_id}/publish`

将行程发布至模板广场。

**请求参数：**

| 参数         | 类型   | 必填 | 说明               |
| :----------- | :----- | :--- | :----------------- |
| title        | string | 是  | 模板标题            |
| description  | string | 是  | 模板简介 (10-200字) |
| is_premium   | bool   | 否  | 是否付费模板(默认否) |

**响应示例：**

```json
{
    "code": 0,
    "message": "模板发布成功，等待审核",
    "data": {
        "template_id": 51,
        "status": "pending"
    }
}
```

---

## 五、模板模块

### 5.1 获取模板列表

**GET** `/template/list`

获取行程模板列表，支持分页和筛选。

**请求参数：**

| 参数         | 类型   | 必填 | 默认值  | 说明                          |
| :----------- | :----- | :--- | :------ | :---------------------------- |
| city_id      | int    | 否  | -       | 按城市筛选                     |
| route_type   | string | 否  | -       | 路线风格: popular/niche       |
| days         | int    | 否  | -       | 按天数筛选                     |
| is_premium   | string | 否  | -       | free/premium                  |
| sort         | string | 否  | hot     | 排序: hot/new                  |
| page         | int    | 否  | 1       | 页码                           |
| page_size    | int    | 否  | 10      | 每页条数                        |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": 1,
                "title": "杭州周末两天游",
                "city": "杭州",
                "days": 2,
                "spot_count": 6,
                "route_type": "popular",
                "use_count": 1234,
                "collect_count": 356,
                "is_premium": "free",
                "cover_image": "https://cdn.example.com/cover/1.jpg"
            }
        ],
        "total": 50,
        "page": 1,
        "page_size": 10,
        "total_pages": 5
    }
}
```

---

### 5.2 获取模板详情

**GET** `/template/{template_id}`

获取模板完整内容。

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "id": 1,
        "title": "杭州周末两天游",
        "description": "适合周末杭州两日游...",
        "city": "杭州",
        "days": 2,
        "route_type": "popular",
        "use_count": 1234,
        "collect_count": 356,
        "is_premium": "free",
        "is_collected": false,
        "author": {
            "id": 5,
            "nickname": "旅行达人"
        },
        "itinerary": [ ... ],
        "total_budget": 500.00,
        "created_at": 1761000000000
    }
}
```

---

### 5.3 使用模板

**POST** `/template/{template_id}/use`

将模板加载为用户个人行程。

**响应示例：**

```json
{
    "code": 0,
    "message": "模板加载成功",
    "data": {
        "trip_id": 105,
        "template_use_count": 1235
    }
}
```

---

### 5.4 收藏/取消收藏模板

**POST** `/template/{template_id}/collect`

**请求参数：**

| 参数     | 类型 | 必填 | 说明                   |
| :------- | :--- | :--- | :--------------------- |
| collect  | bool | 是  | true=收藏, false=取消   |

**响应示例：**

```json
{
    "code": 0,
    "message": "收藏成功",
    "data": {
        "collected": true,
        "collect_count": 357
    }
}
```

---

## 六、对话模块

### 6.1 旅游问答

**POST** `/chat/qa`

发送旅游相关问题，AI 流式返回回答。

**请求参数：**

| 参数    | 类型   | 必填 | 说明               |
| :------ | :----- | :--- | :----------------- |
| message | string | 是  | 问题内容 (1-500字)  |
| city_id | int    | 否  | 关联城市 ID(可选)   |

**响应（流式 SSE）：**

```
data: {"code": 0, "type": "start", "message": "正在思考..."}

data: {"code": 0, "type": "chunk", "content": "西湖"}

data: {"code": 0, "type": "chunk", "content": "景区全天开放"}

data: {"code": 0, "type": "chunk", "content": "，免费参观。"}

data: {"code": 0, "type": "chunk", "content": "\n推荐游览时间："}

data: {"code": 0, "type": "end", "message": "完成"}

```

---

### 6.2 生成行李清单

**POST** `/chat/luggage`

按目的地 / 天数 / 季节生成行李清单。规则化生成（不打大模型，零成本、零延迟），
按 `season` 与城市类型真实分支：夏季出防晒、冬季出羽绒服、≥3 天加换洗数量、
港澳台自动换成证件/签注/转换插头。

**请求参数：**

| 参数   | 类型   | 必填 | 默认值 | 说明                                          |
| :----- | :----- | :--- | :----- | :-------------------------------------------- |
| city   | string | 否   | ""     | 目的地城市名（含"香港/澳门/台湾"时走跨境分支） |
| days   | int    | 否   | 2      | 出行天数（1~15，影响换洗数量与电子设备）       |
| season | string | 否   | 自动   | 季节：夏/冬/春/秋；留空按当前月份推算          |

**响应示例：**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "list": [
            {"group": "证件", "items": ["身份证", "手机（健康码/乘车码）"]},
            {"group": "衣物", "items": ["薄外套", "长袖上衣", "长裤", "舒适运动鞋"]},
            {"group": "洗漱", "items": ["牙刷牙膏", "护肤品", "润唇膏/保湿霜"]},
            {"group": "电子", "items": ["充电宝", "数据线", "耳机"]},
            {"group": "药品", "items": ["创可贴", "肠胃药"]}
        ]
    }
}
```

> 分组固定为 证件/衣物/洗漱/电子/药品 五组；`city` 含"香港"时证件组会变成
> `["港澳通行证及有效签注", "身份证", "少量港币/澳门元现金", "英标转换插头"]`。
```

---

### 6.3 生成美食红黑榜

**POST** `/chat/food`

AI 根据目的地生成美食推荐和避雷清单。

**请求参数：**

| 参数    | 类型 | 必填 | 说明         |
| :------ | :--- | :--- | :----------- |
| city_id | int  | 是  | 目的地城市 ID |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "red_list": [
            {
                "name": "楼外楼",
                "dish": "西湖醋鱼",
                "reason": "百年老店，正宗杭帮菜，环境优雅",
                "avg_price": 120,
                "address": "孤山路30号"
            },
            {
                "name": "知味观",
                "dish": "小笼包",
                "reason": "本地人常去，性价比高",
                "avg_price": 50,
                "address": "仁和路83号"
            }
        ],
        "black_list": [
            {
                "name": "某某特产店",
                "reason": "景区门口高价推销，品质一般",
                "warning": "避开景区门口揽客的店铺"
            }
        ]
    }
}
```

---

## 七、城市与服务模块

### 7.1 获取城市列表

**GET** `/city/list`

获取支持的城市列表。

**请求参数：**

| 参数    | 类型 | 必填 | 默认值 | 说明         |
| :------ | :--- | :--- | :----- | :----------- |
| is_hot  | bool | 否  | -      | 仅返回热门城市 |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": [
        {"id": 1, "name": "杭州", "province": "浙江", "is_hot": true},
        {"id": 2, "name": "成都", "province": "四川", "is_hot": true},
        {"id": 3, "name": "西安", "province": "陕西", "is_hot": true}
    ]
}
```

---

### 7.2 获取服务跳转链接

**GET** `/service/link`

获取指定城市的第三方服务跳转链接列表。

**请求参数：**

| 参数     | 类型 | 必填 | 说明         |
| :------- | :--- | :--- | :----------- |
| city_id  | int  | 是  | 城市 ID       |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": [
        {
            "service_type": "navigate",
            "service_name": "导航",
            "app_id": "wxXXXXXXXXX",
            "path": "pages/index/index?city=杭州",
            "icon_url": "https://cdn.example.com/icons/navigate.png"
        },
        {
            "service_type": "hotel",
            "service_name": "酒店",
            "app_id": "wxXXXXXXXXX",
            "path": "pages/hotel/list?city=杭州&from=zsby",
            "icon_url": "https://cdn.example.com/icons/hotel.png"
        },
        {
            "service_type": "taxi",
            "service_name": "打车",
            "app_id": "wxXXXXXXXXX",
            "path": "pages/index/index?city=杭州",
            "icon_url": "https://cdn.example.com/icons/taxi.png"
        }
    ]
}
```

---

## 八、收藏模块

### 8.1 获取收藏列表

**GET** `/collection/list`

获取用户收藏的**模板**列表。返回的是完整模板字段（不是收藏记录 id），
前端可直接拿去开 `/template/detail`。

**请求参数：** 无

**响应示例：**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "list": [
            {
                "id": 1,
                "collection_id": 3,
                "title": "杭州2日经典西湖游",
                "city": "杭州",
                "days": 2,
                "cover": "🏞️",
                "route_type": "popular",
                "uses": 100,
                "spots_count": 6
            }
        ]
    }
}
```

> `id` 是**模板 id**（用于打开详情）；`collection_id` 是收藏记录 id，仅用于排查。
> 同一用户对同一模板只会有一条收藏记录（数据库唯一索引兜底并发重复点击）。

---

### 8.2 添加收藏

**POST** `/collection/add`

> 原文档写的 `/collection/toggle` 与实际实现不符——实际只有 add，没有取消接口，
> 也没有 `target_type` 维度（收藏对象固定为模板）。

**请求参数：**

| 参数        | 类型   | 必填 | 说明                |
| :---------- | :----- | :--- | :------------------ |
| 参数        | 类型   | 必填 | 说明                |
| :---------- | :----- | :--- | :------------------ |
| template_id | int    | 是  | 模板 id             |

**响应示例：**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "collected": true,
        "duplicated": false
    }
}
```

> `duplicated: true` 表示该模板之前已收藏（幂等，不会插入第二条）。
> 模板不存在返回 `code: 404`；缺 `template_id` 返回 HTTP 422。

---

## 九、会员与订单模块

### 9.1 获取会员状态

**GET** `/membership/status`

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "is_vip": false,
        "role": "free",
        "vip_expire_time": null,
        "plan_type": null,
        "benefits": {
            "daily_limit": 3,
            "daily_remaining": 2,
            "can_use_niche": false,
            "can_use_ocr": false,
            "has_ads": true,
            "can_use_premium_template": false
        }
    }
}
```

---

### 9.2 创建订单

**POST** `/order/create`

创建会员充值订单。

**请求参数：**

| 参数      | 类型   | 必填 | 说明                   |
| :-------- | :----- | :--- | :--------------------- |
| plan_type | string | 是  | monthly/yearly         |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "order_id": 201,
        "order_no": "ZSBY20260806180000001",
        "plan_type": "yearly",
        "amount": 129.00,
        "pay_params": {
            "appId": "wxXXXXXXXX",
            "timeStamp": "1722940800",
            "nonceStr": "abc123",
            "package": "prepay_id=wx20260806180000001",
            "signType": "RSA",
            "paySign": "XXXXXX..."
        }
    }
}
```

---

### 9.3 支付回调

**POST** `/pay/callback`

微信支付异步回调接口（由微信服务器调用）。

**说明：** 接收微信支付结果通知，验证签名后更新订单和会员状态。

**响应：**

```json
{
    "code": "SUCCESS",
    "message": "成功"
}
```

---

### 9.4 获取订单列表

**GET** `/order/list`

**请求参数：**

| 参数       | 类型 | 必填 | 默认值 | 说明         |
| :--------- | :--- | :--- | :----- | :----------- |
| pay_status | string | 否 | -    | unpaid/paid  |
| page       | int  | 否  | 1     | 页码         |
| page_size  | int  | 否  | 20    | 每页条数     |

**响应示例：**

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": 201,
                "order_no": "ZSBY20260806180000001",
                "plan_type": "yearly",
                "amount": 129.00,
                "pay_status": "paid",
                "transaction_id": "420000XXXXX",
                "paid_at": 1761000000000,
                "created_at": 1761000000000
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "total_pages": 1
    }
}
```

---

## 十、接口汇总表（实现态真值，共 45 个业务接口）

> 本表由 `server/app/routers/*.py` 的路由声明扫描生成，与代码一致。「认证」列为该接口是否挂了 `Depends(get_current_user)`。返回统一 `{code, msg, data}`。另有 `GET /` 与 `GET /api/health` 两个探活接口直接声明在 `app/main.py`，不计入这 45 个。

| 模块 | 方法 | 路径 | 说明 | 认证 |
| :--- | :--- | :--- | :--- | :--- |
| 认证 | POST | /api/auth/login | 微信 code 换 token（无 AppID 时返回 mock） | 否 |
| 认证 | POST | /api/auth/bind-phone | 已登录用户绑定手机号 | 是 |
| 认证 | POST | /api/auth/phone-login | 手机号 + 验证码登录 | 否 |
| 规划 | POST | /api/plan/form | 表单规划生成行程（受每日限流 + 积分） | 是 |
| 规划 | POST | /api/plan/quick | 一句话快规划 | 是 |
| 规划 | POST | /api/plan/chat-adjust | 对话微调行程 | 是 |
| 行程 | GET | /api/trip/list | 我的行程列表（status: active/all） | 是 |
| 行程 | GET | /api/trip/detail | 行程详情 | 是 |
| 行程 | POST | /api/trip/save | 保存行程（整体 JSON 存 `trips.content`） | 是 |
| 行程 | POST | /api/trip/delete | 删除行程 | 是 |
| 模板 | GET | /api/template/hot | 精选模板列表 | 是 |
| 模板 | GET | /api/template/detail | 模板详情 | 是 |
| 模板 | POST | /api/template/use | 模板加载为行程 | 是 |
| 模板 | POST | /api/template/publish | 行程发布为模板 | 是 |
| 模板 | GET | /api/template/published | 我发布的模板 | 是 |
| 对话 | POST | /api/chat/qa | 流式问答（SSE）：先检索，检索为空直接拒答 | 是 |
| 对话 | POST | /api/chat/luggage | 行李清单 | 是 |
| 对话 | POST | /api/chat/food | 美食红黑榜 | 是 |
| 对话 | GET | /api/chat/rag_stats | RAG 可观测性：提问数、有依据率、拒答率、索引状态 | 是 |
| 知识检索 | GET | /api/kb/status | 索引是否已建、文档数与城市覆盖 | 是 |
| 知识检索 | GET | /api/kb/search | 只读检索调试接口 | 是 |
| 地图 | GET | /api/map/reverse-geocode | 经纬度 → 城市名（gcj-02，与 `wx.getLocation` 同系） | 是 |
| 地图 | GET | /api/map/geocode | 地名/车站 → 经纬度（腾讯优先，逐级降级） | 是 |
| 地图 | GET | /api/map/geocode-batch | 批量地理编码（景点距离计算用），顺序与输入一致 | 是 |
| 识图 | POST | /api/ocr/recognize | 截图识行程 / 识别视频 | 是 |
| 票务 | GET | /api/ticket/search | 12306 余票车次，失败降级估算 | 是 |
| 票务渠道 | GET | /api/ota/channels | 购票/团购/订房渠道列表（含搜索深链），离线可用 | 是 |
| 票务渠道 | GET | /api/ota/price | 实时价格（预留，当前恒返 `available=False`） | 是 |
| 服务 | GET | /api/service/list | 第三方小程序跳转白名单 | 否 |
| 收藏 | GET | /api/collection/list | 收藏列表 | 是 |
| 收藏 | POST | /api/collection/add | 收藏模板（新增接口，无 toggle） | 是 |
| 会员 | GET | /api/membership/plans | 会员套餐 | 是 |
| 会员 | POST | /api/membership/order | 创建支付订单（演示态，无微信回调） | 是 |
| 用户 | GET | /api/user/me | 当前用户完整信息（含会员态字段） | 是 |
| 用户 | POST | /api/user/profile | 更新头像/昵称 | 是 |
| 用户 | POST | /api/user/avatar | 上传头像并返回永久 URL | 是 |
| 用户 | POST | /api/user/feedback | 提交意见反馈 | 是 |
| 用户 | POST | /api/user/deactivate | 注销账号（软删除，`is_active=False`） | 是 |
| 用户 | GET | /api/user/stats | 行程数、去过的城市数 | 是 |
| 用户 | GET | /api/user/points | 积分余额 | 是 |
| 用户 | POST | /api/user/recharge | 人工充值申请（管理员线下确认后加积分） | 是 |
| 短信 | POST | /api/sms/send | 发送短信验证码 | 否 |
| 分销 | POST | /api/distribution/bind | 绑定邀请关系 | 是 |
| 分销 | GET | /api/distribution/my | 我的分销记录与佣金 | 是 |
| 埋点 | POST | /api/track | 批量上报埋点事件，失败不阻塞主流程 | 是 |

### 10.1 设计态与实现态的差异

前 9 节按 RESTful 风格设计，实际落地统一改成 `/api/模块/动作`，因此下列设计态路径**在代码中不存在**（括号内是实现态的对应物）：

- `GET/PUT /api/user/info` → `/api/user/me`、`/api/user/profile`
- `GET /api/user/quota` → 限流计数走 Redis，未单独暴露查询接口（会员态见 `/api/user/me`）
- **每日限流与积分的错误码**（2026-10-23 起真实生效，此前 `quota_service` 是死代码）：
  - `code: 4002` — 今日免费生成次数已用完（`DAILY_PLAN_LIMIT`，默认 3 次/天，会员不限）
  - `code: 4001` — 积分不足（仅 `MONETIZATION_ENABLED=true` 时扣费）
  - 两个接口：`POST /api/plan/form`、`POST /api/plan/quick`；`POST /api/plan/chat-adjust` 只扣积分不占每日配额
  - 配额先扣、积分后扣，积分不足时配额会回滚，不会白占用户当日额度
- `POST /api/plan/ocr` → `/api/ocr/recognize`
- `POST /api/plan/adjust` → `/api/plan/chat-adjust`
- `GET/PUT/DELETE /api/trip/{id}`、`POST /api/trip`、`POST /api/trip/{id}/publish` → `/api/trip/detail`、`/api/trip/save`、`/api/trip/delete`、`/api/template/publish`
- `GET /api/template/list`、`/api/template/{id}`、`/api/template/{id}/use`、`/api/template/{id}/collect` → `/api/template/hot`、`/api/template/detail`、`/api/template/use`、`/api/collection/add`
- `GET /api/city/list` → 无对应接口：城市列表由前端 `utils/cities.js` 内置（`cities` 表已于 2026-10-22 从代码删除）
- `GET /api/service/link` → `/api/service/list`（渠道硬编码在路由的 `SERVICES` 常量；`service_links` 表同样已删除）
- `POST /api/collection/toggle` → `/api/collection/add`（只加不减，取消收藏未实现）
- `GET /api/membership/status` → `/api/user/me`（会员态是 `users.is_vip` 字段，未建 membership 表）
- `POST /api/order/create`、`GET /api/order/list`、`POST /api/pay/callback` → `/api/membership/order`；支付回调未实现（无企业主体，支付为演示态）

实现态新增、前 9 节未覆盖的模块：`kb`（知识检索）、`map`（地理编码）、`ota`（购票渠道）、`ticket`（12306）、`track`（埋点）、`distribution`（分销）、`sms`（短信）、`collection`、`user` 的积分/注销/统计。

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    app_env: str = "development"

    # CORS 白名单：逗号分隔的完整 Origin，例如
    #   CORS_ORIGINS=https://你的域名,https://api.你的域名
    # 小程序原生 wx.request 不受浏览器同源策略约束，这里只约束 H5/网页端来源。
    # 留空且 app_env 非 production 时自动放行 localhost 与局域网（真机联调要）；
    # 上线时把 app_env 设成 production，局域网放行会自动关闭，只认白名单。
    cors_origins: str = ""

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    database_url: str = "sqlite+aiosqlite:///./banyou.db"
    redis_url: str = ""

    # 后端对外可访问的基础 URL，用于生成头像等静态资源永久链接
    # 示例：http://192.168.101.236:8009 或 https://your-domain.com
    public_base_url: str = ""

    wx_app_id: str = ""
    wx_app_secret: str = ""

    jwt_secret: str = "dev-secret-change-me-please-replace-32bytes-min"
    jwt_expire_hours: int = 168

    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    llm_thinking: bool = False

    # —— 检索增强（RAG）——
    # 留空则复用上面视觉模型那套 url/key（百炼同一个账号即可出 embedding，无需新增凭据）。
    embedding_api_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-v3"

    # 向量存储（Milvus）。留空 = 不启用向量检索，检索退回关键词匹配。
    # 两种形态同一个配置项：本地文件路径 = milvus-lite 内嵌（开发机直接可用，
    # 例如 kb/corpus/milvus.db）；http://host:19530 = 连独立 Milvus 服务（容器部署）。
    # 变量名必须带 KB_ 前缀：pymilvus 在自己的 settings.py 里 load_dotenv() 并读取
    # MILVUS_URI，import 时就解析它，非 http 形式会抛 ConnectionConfigException——
    # 那个异常被 retriever.client() 吞掉后只会静默退回关键词匹配，很难查。
    kb_milvus_uri: str = ""
    kb_milvus_collection: str = "kb_docs"
    # 官方 Milvus 开启鉴权后为 "用户名:密码"；milvus-lite 不需要。
    kb_milvus_token: str = ""

    daily_plan_limit: int = 3

    # 积分制（登录送积分，AI 生成扣积分，用完人工充值）
    points_signup: int = 20        # 注册/首次登录赠送积分
    points_per_plan: int = 10      # 每次 AI 生成行程消耗积分
    points_per_chat: int = 2       # 每次 AI 问答消耗积分

    # 是否开启变现功能（会员/积分充值/分销佣金）。
    # false = 个人主体上架：AI 生成与问答不扣积分、不拦截，会员/积分入口在前端隐藏。
    # true  = 企业/个体工商户主体：启用积分扣减与会员闭环（需 .env 同时配置微信支付）。
    # 默认关闭，与前端 config/env.js 的 MONETIZATION_ENABLED 保持一致。
    monetization_enabled: bool = False

    # 视觉多模态模型（识图/识别视频用，当前行程生成的 DeepSeek 为纯文本不可用）
    # 支持 OpenAI 兼容协议：通义千问 Qwen-VL、GPT-4o、Gemini 等。
    # 获取示例：阿里云百炼 https://dashscope.console.aliyun.com/ → 开通 qwen-vl 系列
    vision_api_key: str = ""
    vision_api_url: str = ""   # 例如 https://api.openai.com/v1 或 https://dashscope.aliyuncs.com/compatible-mode/v1
    vision_model: str = "qwen-vl-max"  # 视觉模型名，按服务商调整

    ocr_api_key: str = ""
    ocr_secret_key: str = ""

    # 短信服务（手机号验证码登录注册用）。key 到位前走 mock，send 接口会返回 dev_code 便于本地测试。
    # provider 可选：aliyun(官方Dysmsapi) / alicloud-market(阿里云市场「三网106短信」网关) / chuangxin / luosimao。
    sms_provider: str = "aliyun"
    sms_api_key: str = ""
    sms_api_secret: str = ""
    sms_sign_name: str = ""        # 短信签名（如「知途旅行」）
    sms_template_code: str = ""    # 短信模板 CODE（如阿里云 SMS_xxxxxxxxxxx）

    # 阿里云市场「三网106短信」网关（provider=alicloud-market 时生效）。
    # 接口文档：POST {sms_market_url}，鉴权用 APPCODE（Header: Authorization: APPCODE <AppCode>）。
    # 请求体：mobile=手机号&templateId=模板ID&smsSignId=签名ID&param={"code":"12345"}
    sms_app_code: str = ""         # 阿里云市场控制台「APPCODE」
    sms_market_url: str = "https://gyytz.market.alicloudapi.com/sms/smsSend"
    sms_market_template_id: str = ""   # 短信模板 ID（如 908e94cc0f8b4476）
    sms_market_sign_id: str = ""       # 短信签名 ID（如 2e65b1bb3d05446）

    # 阿里云市场「创信短信」网关（provider=chuangxin 时生效）。
    # 接口：POST {chuangxin_url}，鉴权用 APPCODE（Header: Authorization: APPCODE <AppCode>）。
    # 请求参数 (Query)：mobile=手机号&content=短信内容（签名直接写在内容里，如「【创信】你的验证码是：5」）。
    chuangxin_app_code: str = ""   # 阿里云市场控制台「APPCODE」
    chuangxin_url: str = "https://cxkjsms.market.alicloudapi.com/chuangxinsms/dxjk"
    chuangxin_sign: str = "创信"   # 短信签名，会拼成「【创信】...」

    # 螺丝帽 Luosimao（provider=luosimao 时生效）
    # 官网：https://luosimao.com/service/sms
    # 接口：POST https://sms-api.luosimao.com/v1/send.json，Basic Auth（用户名 api，密码 key-...）
    # 签名需在后台申请，如「知途旅行」；message 末尾必须带签名，例如：验证码：123456【知途旅行】
    luosimao_key: str = ""         # API Key，形如 key-d609b7692...
    luosimao_sign: str = ""        # 短信签名，如「知途旅行」

    wx_mch_id: str = ""
    wx_api_v3_key: str = ""

    # 分销佣金（CPS）：邀请人获得被邀请人付费金额的一定比例
    commission_rate: float = 0.30        # 默认 30%
    invite_code_len: int = 6             # 邀请码长度（大写字母+数字）

    # 真实票务：本地 12306-mcp（Node 进程，HTTP 模式 --port）的 MCP endpoint。
    # 启动示例：npx -y 12306-mcp --port 8801  →  endpoint 为 http://127.0.0.1:8801/mcp
    # 留空则不调用，search 接口直接返回离线估算兜底。
    ticket_mcp_url: str = "http://127.0.0.1:8801/mcp"

    # 腾讯位置服务 WebService（地理编码：地名/景点 → 经纬度，gcj-02 坐标，
    # 与 wx.getLocation(type=gcj02) 及 wx.openLocation 同一坐标系，零偏移匹配）。
    # 开通：https://lbs.qq.com → 创建应用 → 选「WebServiceAPI」→ 拿到 key。
    # 填后景点/地名即可拿到真实坐标（用于"距您 X km"与导航）；不填则走内置坐标表兜底。
    tencent_lbs_key: str = ""

    # 高德地图 MCP（站点/地名 → 经纬度，用于"在地图看站点"精准定位+导航）。
    # 留空则走内置热门站点坐标表（零依赖，开发阶段即可用）。
    # 来源二选一：
    #  A) ModelScope 社区版「GaodeMapPro」(mako2026)，Hosted 免 Key：在 ModelScope MCP 广场搜 GaodeMapPro，
    #     复制其 Hosted 的 streamable-HTTP 地址（形如 https://mcp.api-inference.modelscope.net/<id>/mcp）填入下方。
    #  B) 官方高德 MCP（mcp.amap.com/sse?key=你的KEY），需先在 https://console.amap.com 申请 Web 服务 Key；
    #     官方工具名为 maps_geo，请把 gaode_geocode_tool 改为 maps_geo。
    gaode_mcp_url: str = ""
    gaode_geocode_tool: str = "geocode"

    # 高德开放平台 Web 服务 Key（REST 直连地理编码，备用）。
    # 优先级：腾讯 LBS > 高德 MCP > 高德 REST > 内置坐标表。
    gaode_web_key: str = ""

    @model_validator(mode="after")
    def _guard_production_secrets(self):
        """生产环境禁止带着默认开发密钥上线。

        jwt_secret 是 HS256 的签名密钥，一旦沿用默认值，任何人都能伪造
        任意 user_id 的 token——不需要登录就能读写别人的行程。
        """
        if self.app_env == "production":
            if self.jwt_secret.startswith("dev-secret-change-me") or len(self.jwt_secret) < 32:
                raise ValueError(
                    "生产环境必须配置 JWT_SECRET（≥32 位随机串），不能使用默认开发密钥"
                )
            if not self.redis_url:
                raise ValueError(
                    "生产环境必须配置 REDIS_URL：每日限流、短信验证码、发送频率限制、"
                    "微信 access_token 缓存都靠它。没有 Redis 时这些会静默降级成进程内计数，"
                    "多 worker 下额度直接翻倍。单机部署可用 docker 起一个 redis:7-alpine。"
                )
        return self


settings = Settings()

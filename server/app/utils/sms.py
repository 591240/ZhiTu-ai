import asyncio
import httpx

from app.config import settings

try:
    from alibabacloud_dysmsapi20170525 import client as dysms_client
    from alibabacloud_dysmsapi20170525 import models as dysms_models
    from alibabacloud_tea_openapi import models as open_api_models
    _HAS_ALIYUN_SMS = True
except Exception:  # 未安装 SDK 时不阻塞模块导入
    _HAS_ALIYUN_SMS = False


def _mock_send(phone: str, code: str, missing: str):
    """未配置短信服务时的降级。

    开发态：打印并把验证码回传前端，方便本地登录；
    生产态：直接失败。否则一旦漏配 key，/api/sms/send 会把验证码原样返回，
    等于任何人都能以任意手机号登录。
    """
    if settings.app_env == "production":
        raise RuntimeError(f"短信服务未配置（{missing}），生产环境拒绝发送验证码")
    print(f"[SMS-MOCK] 给 {phone} 发送验证码: {code}（未配置 {missing}，仅本地测试）")
    return True, code


async def send_sms(phone: str, code: str):
    """发送短信验证码。

    返回 (success: bool, dev_code: str | None)。
    - 未配置短信 key 且非生产环境：dev_code 回传前端（本地开发用）。
    - 生产环境未配置 key：抛错，绝不静默降级成"谁都能登录"。
    - 已配置 key 时走真实服务商，dev_code 为 None。
    """
    provider = settings.sms_provider

    if provider == "alicloud-market":
        if not settings.sms_app_code:
            return _mock_send(phone, code, "SMS_APP_CODE")
        ok = await _send_market(phone, code)
        return ok, None
    if provider == "luosimao":
        if not settings.luosimao_key:
            return _mock_send(phone, code, "LUOSIMAO_KEY")
        ok = await _send_luosimao(phone, code)
        return ok, None
    if provider == "chuangxin":
        if not settings.chuangxin_app_code:
            return _mock_send(phone, code, "CHUANGXIN_APP_CODE")
        ok = await _send_chuangxin(phone, code)
        return ok, None
    if not settings.sms_api_key:
        return _mock_send(phone, code, "SMS_API_KEY")

    if provider == "aliyun":
        ok = await _send_aliyun(phone, code)
        return ok, None
    # 腾讯云等其他服务商在 key 到位后扩展：
    # if provider == "tencent":
    #     return await _send_tencent(phone, code), None

    print(f"[SMS] 未知的短信服务商: {provider}")
    return False, None


async def _send_aliyun(phone: str, code: str) -> bool:
    """阿里云短信发送（官方 SDK dysmsapi20170525）。

    需要 .env 配置：SMS_API_KEY / SMS_API_SECRET / SMS_SIGN_NAME / SMS_TEMPLATE_CODE。
    模板需含 ${code} 变量（如「您的验证码为${code}，5分钟内有效」）。
    发送为同步 SDK，用 asyncio.to_thread 避免阻塞事件循环。
    """
    if not _HAS_ALIYUN_SMS:
        print("[SMS] 阿里云短信 SDK 未安装，无法发送真实短信")
        return False
    missing = [k for k, v in {
        "SMS_API_KEY": settings.sms_api_key,
        "SMS_API_SECRET": settings.sms_api_secret,
        "SMS_SIGN_NAME": settings.sms_sign_name,
        "SMS_TEMPLATE_CODE": settings.sms_template_code,
    }.items() if not v]
    if missing:
        print(f"[SMS] 阿里云短信配置缺失: {missing}，退回 mock（不真实发送）")
        return False
    try:
        config = open_api_models.Config(
            access_key_id=settings.sms_api_key,
            access_key_secret=settings.sms_api_secret,
        )
        config.endpoint = "dysmsapi.aliyuncs.com"
        cli = dysms_client.Client(config)
        req = dysms_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=settings.sms_sign_name,
            template_code=settings.sms_template_code,
            template_param=f'{{"code":"{code}"}}',
        )
        resp = await asyncio.to_thread(cli.send_sms, req)
        body = resp.body
        if body.code == "OK":
            print(f"[SMS] 已向 {phone} 发送验证码（阿里云）")
            return True
        print(f"[SMS] 阿里云发送返回非 OK: code={body.code} message={body.message}")
        return False
    except Exception as e:
        print(f"[SMS] 阿里云发送异常: {e}")
        return False


async def _send_market(phone: str, code: str) -> bool:
    """阿里云市场「三网106短信」网关（provider=alicloud-market）。

    接口：POST {sms_market_url}，鉴权用 APPCODE（Header: Authorization: APPCODE <AppCode>）。
    请求体（form）：mobile / templateId / smsSignId / param（JSON 串 {"code":"12345"}）。
    参考你的调试页面参数：templateId=908e94cc0f8b4476, smsSignId=2e65b1bb3d05446。
    """
    missing = [k for k, v in {
        "SMS_APP_CODE": settings.sms_app_code,
        "SMS_MARKET_TEMPLATE_ID": settings.sms_market_template_id,
        "SMS_MARKET_SIGN_ID": settings.sms_market_sign_id,
    }.items() if not v]
    if missing:
        print(f"[SMS] 阿里云市场短信配置缺失: {missing}，退回 mock（不真实发送）")
        return False
    url = settings.sms_market_url
    headers = {
        "Authorization": f"APPCODE {settings.sms_app_code}",
    }
    # 该网关参数通过 Query String 传递（调试页面显示「请求参数 (Query)」）
    params = {
        "mobile": phone,
        "templateId": settings.sms_market_template_id,
        "smsSignId": settings.sms_market_sign_id,
        "param": f'{{"code":"{code}"}}',
    }
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            resp = await client.post(url, headers=headers, params=params)
        text = resp.text
        print(f"[SMS] 阿里云市场请求 URL: {resp.request.url}")
        print(f"[SMS] 阿里云市场请求 headers: {dict(resp.request.headers)}")
        print(f"[SMS] 阿里云市场返回 HTTP {resp.status_code}: {text[:200]}")
        if resp.status_code == 200:
            # 成功响应：{"code":"0","msg":"成功",...}；兼容部分网关返回 "success"
            try:
                body = resp.json()
                biz_code = str(body.get("code", ""))
                if biz_code == "0" or "成功" in str(body.get("msg", "")) or "success" in text.lower():
                    print(f"[SMS] 已向 {phone} 发送验证码（阿里云市场网关）")
                    return True
            except Exception:
                if "success" in text.lower():
                    print(f"[SMS] 已向 {phone} 发送验证码（阿里云市场网关）")
                    return True
        return False
    except Exception as e:
        print(f"[SMS] 阿里云市场发送异常: {e}")
        return False


async def _send_luosimao(phone: str, code: str) -> bool:
    """螺丝帽 Luosimao 短信发送（provider=luosimao）。

    官网：https://luosimao.com/docs/api/sms/send
    接口：POST https://sms-api.luosimao.com/v1/send.json
    鉴权：HTTP Basic Auth，用户名固定为 api，密码为 settings.luosimao_key。
    参数：mobile / message（末尾必须含签名，如「验证码：654321【知途旅行】」）。
    成功返回：{"error": 0, "msg": "ok"}
    """
    if not settings.luosimao_sign:
        print("[SMS] 螺丝帽短信配置缺失: LUOSIMAO_SIGN")
        return False
    url = "https://sms-api.luosimao.com/v1/send.json"
    message = f"您的验证码是{code}，5分钟内有效，请勿泄露。【{settings.luosimao_sign}】"
    data = {"mobile": phone, "message": message}
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            resp = await client.post(url, data=data, auth=("api", settings.luosimao_key))
        text = resp.text
        print(f"[SMS] 螺丝帽返回 HTTP {resp.status_code}: {text[:200]}")
        if resp.status_code == 200:
            try:
                body = resp.json()
                if body.get("error") == 0:
                    print(f"[SMS] 已向 {phone} 发送验证码（螺丝帽）")
                    return True
                print(f"[SMS] 螺丝帽返回错误: error={body.get('error')} msg={body.get('msg')}")
                return False
            except Exception:
                if "ok" in text.lower():
                    print(f"[SMS] 已向 {phone} 发送验证码（螺丝帽）")
                    return True
        return False
    except Exception as e:
        print(f"[SMS] 螺丝帽发送异常: {e}")
        return False


async def _send_chuangxin(phone: str, code: str) -> bool:
    """阿里云市场「创信短信」网关（provider=chuangxin）。

    接口：POST https://cxkjsms.market.alicloudapi.com/chuangxinsms/dxjk
    鉴权：Header Authorization: APPCODE <AppCode>
    参数：Query String 传 mobile / content；签名直接写在 content 中。
    内容示例：【创信】你的验证码是：5，5分钟内有效，请勿泄露。
    """
    missing = [k for k, v in {
        "CHUANGXIN_APP_CODE": settings.chuangxin_app_code,
        "CHUANGXIN_SIGN": settings.chuangxin_sign,
    }.items() if not v]
    if missing:
        print(f"[SMS] 创信短信配置缺失: {missing}，退回 mock（不真实发送）")
        return False
    url = settings.chuangxin_url
    headers = {
        "Authorization": f"APPCODE {settings.chuangxin_app_code}",
    }
    content = f"【{settings.chuangxin_sign}】你的验证码是：{code}，5分钟内有效，请勿泄露。"
    params = {
        "mobile": phone,
        "content": content,
    }
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            resp = await client.post(url, headers=headers, params=params)
        text = resp.text
        print(f"[SMS] 创信请求 URL: {resp.request.url}")
        print(f"[SMS] 创信请求 headers: {dict(resp.request.headers)}")
        print(f"[SMS] 创信返回 HTTP {resp.status_code}: {text[:500]}")
        if resp.status_code == 200:
            try:
                body = resp.json()
                biz_code = str(body.get("code", ""))
                status = str(body.get("Status", ""))
                # 创信成功返回：{"Status":"Success","Message":"ok",...}
                # 同时兼容其他网关 code:0 / success / OK 等返回
                if (status == "Success" or
                        biz_code in ("0", "200", "OK") or
                        "success" in text.lower() or
                        "成功" in text or
                        body.get("Message") == "ok"):
                    print(f"[SMS] 已向 {phone} 发送验证码（创信）")
                    return True
                print(f"[SMS] 创信返回业务错误: code={biz_code} status={status} body={text[:200]}")
                return False
            except Exception:
                # 非 JSON 但包含成功字样也算成功
                if "success" in text.lower() or "成功" in text or "ok" in text.lower():
                    print(f"[SMS] 已向 {phone} 发送验证码（创信）")
                    return True
        return False
    except Exception as e:
        print(f"[SMS] 创信发送异常: {type(e).__name__}: {e!r}")
        return False

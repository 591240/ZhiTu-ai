// config/env.js —— 环境配置
// 已移除 mock 模式：前端一律请求真实后端（miniprogram 里不再有本地示例数据分支）。

const env = {
  APP_NAME: '知途 AI 旅行',

  // 是否开启「变现功能」（会员订阅 / 积分充值 / 分销佣金）。
  //  false = 个人主体上架：移除一切付费能力，App 作为纯免费 AI 行程工具发布。
  //          AI 生成与问答不再扣积分，会员/积分/邀请入口全部隐藏，手机号一键绑定也禁用。
  //  true  = 企业/个体工商户主体：启用会员订阅与积分充值闭环（需在 .env 同步配置微信支付）。
  //  ⚠️ 当前按【个人主体】上架，默认关闭。将来注册个体户后，把这里和后端 .env 的
  //      MONETIZATION_ENABLED 都改为 true 即可重新开启变现，无需改业务代码。
  MONETIZATION_ENABLED: false,

  // 后端地址（唯一需要按环境改的地方）
  //  · 本地模拟器：http://127.0.0.1:8000
  //  · 真机联调：填电脑局域网 IP（手机与电脑同一路由器），并在开发者工具
  //    「详情 → 本地设置」勾选「不校验合法域名」
  //  · 上线：必须 HTTPS 公网域名，并在公众平台「开发设置 → 服务器域名 →
  //    request 合法域名」添加；图片域名同理（uploadFile / downloadFile 也要加）
  //  ⚠️ 笔记本切网（有线↔无线）后 IP 会变，真机突然全部超时先 ipconfig 确认。
  BASE_URL: 'http://192.168.10.8:8000',

  // 微信小程序 AppID：登录 mp.weixin.qq.com → 开发管理 → 开发设置 → AppID(小程序ID)
  // 注册即有（无需上线）；测试号不支持跳转第三方小程序，必须用真实 AppID
  WX_APP_ID: 'wxf5fd654f184a0bb7',

  // 免费用户每日 AI 行程生成限额（仅用于前端文案展示；真实限制在后端
  // DAILY_PLAN_LIMIT + quota_service，改这里不会生效）
  DAILY_PLAN_LIMIT: 3,

  // === 快捷服务跳转映射：服务 key -> 第三方小程序 ===
  // appId 为公开可查的真实小程序 AppID。
  // 必须在本小程序公众平台后台「设置 → 第三方设置 → 跳转小程序」白名单中登记，
  // 否则真机 wx.navigateToMiniProgram 调用会失败（开发者工具不校验，需真机测）。
  SERVICE_LINKS: {
    map:    { appId: 'wxca942bbff22e0e51', name: '腾讯地图' },
    car:    { appId: 'wxaf35009675aa0b2a', name: '滴滴出行' },
    hotel:  { appId: 'wx0e6ed4f51db9d078', name: '携程旅行' },
    food:   { appId: 'wxde8ac0a21135c07d', name: '美团' },
    flight: { appId: 'wx0e6ed4f51db9d078', name: '携程旅行' },
    ticket: { appId: 'wx0e6ed4f51db9d078', name: '携程旅行' },
    movie:  { appId: 'wxde8ac0a21135c07d', name: '美团' },
    takeout:{ appId: 'wxde8ac0a21135c07d', name: '美团' }
  }
}

module.exports = env

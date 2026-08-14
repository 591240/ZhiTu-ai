// config/env.js —— 环境配置
// USE_MOCK=true 时前端使用本地示例数据，无需后端即可在微信开发者工具预览全部页面。
// 接入真实后端时：把 USE_MOCK 改为 false，并填好 BASE_URL / WX_APP_ID。

const env = {
  APP_NAME: '知途 AI 旅行',

  // 是否开启「变现功能」（会员订阅 / 积分充值 / 分销佣金）。
  //  false = 个人主体上架：移除一切付费能力，App 作为纯免费 AI 行程工具发布。
  //          AI 生成与问答不再扣积分，会员/积分/邀请入口全部隐藏，手机号一键绑定也禁用。
  //  true  = 企业/个体工商户主体：启用会员订阅与积分充值闭环（需在 .env 同步配置微信支付）。
  //  ⚠️ 当前按【个人主体】上架，默认关闭。将来注册个体户后，把这里和后端 .env 的
  //      MONETIZATION_ENABLED 都改为 true 即可重新开启变现，无需改业务代码。
  MONETIZATION_ENABLED: false,

  // 是否使用本地 Mock 数据（无后端也能跑通演示）
  // 切 false 前必须填好 BASE_URL(真实后端) + WX_APP_ID(自己小程序)，
  // 并在开发者工具勾选「详情 → 本地设置 → 不校验合法域名」。
  //  ⚠️ 演示/真机预览默认开 true：手机离线即可跑全部页面，无需后端与域名。
  //  —— 2026-08-13：已切 false 联调真后端（DeepSeek 实时生成）。
  USE_MOCK: false,

  // 真实后端地址（USE_MOCK=false 时才生效）：
  //  · 本地开发预览：填 http://127.0.0.1:8001（8000 端口被旧后端进程占用）。
  //    ⚠️ 当前 8001 被一个旧代码进程占用且沙箱无法终止，新代码后端临时跑在 8008，
  //      且 8008 仅绑 127.0.0.1（手机连不上），故另起一个绑 0.0.0.0 的实例在 8009 供真机联调。
  //    前端接口统一以 /api 开头，BASE_URL 不含 /api
  //  · 真机 / 上线：必须填 HTTPS 公网域名（如 https://api.你的域名.com），并在公众平台「开发设置 → 服务器域名 → request 合法域名」添加
  //  —— 当前联调用电脑局域网 IP（手机与电脑同一路由器）：
  //    注意：电脑从以太网切到 WLAN 后 IP 会变化，若真机突然全部超时，先 ipconfig 确认本机 IP。
  BASE_URL: 'http://192.168.10.8:8009',

  // 微信小程序 AppID：登录 mp.weixin.qq.com → 开发管理 → 开发设置 → AppID(小程序ID) 复制填写
  // 注册即有（无需上线）；测试号不支持跳转，必须用真实 AppID
  WX_APP_ID: 'wxf5fd654f184a0bb7',

  // 免费用户每日 AI 行程生成限额
  DAILY_PLAN_LIMIT: 3,

  // === 快捷服务跳转映射：服务 key -> 第三方小程序 ===
  // appId 为公开可查的真实小程序 AppID（详见项目沟通记录）。
  // 必须在本小程序公众平台后台「设置 → 第三方设置 → 跳转小程序」白名单中登记，
  // 否则真机 wx.navigateToMiniProgram 调用会失败（开发者工具不校验，需真机测）。
  // 8 个入口收敛为 4 个高频 AppID，白名单（上限 10）还余 6 个名额，可继续扩展。
  // 注意：美团 AppID 有来源冲突，上线前请用「手机微信 → 该小程序 → 更多资料」核实。
  SERVICE_LINKS: {
    map:    { appId: 'wx761430a892e5b19f', name: '腾讯地图' }, // 导航
    car:    { appId: 'wxaf35009675aa0b2a', name: '滴滴出行' }, // 打车（高可信）
    hotel:  { appId: 'wx0e6ed4f51db9d078', name: '携程旅行' }, // 酒店
    food:   { appId: 'wxde8ac0a21135c07d', name: '美团' },     // 美食（AppID 待核实）
    flight: { appId: 'wxb84362f15c06b3f2', name: '铁路12306' }, // 机票高铁（火车票官方渠道，查票/购票最权威）
    ticket: { appId: 'wx0e6ed4f51db9d078', name: '携程旅行' }, // 景区门票
    movie:  { appId: 'wxde8ac0a21135c07d', name: '美团' },     // 电影票（猫眼在美团内）
    takeout:{ appId: 'wxde8ac0a21135c07d', name: '美团' }      // 外卖（AppID 待核实）
  }
}

module.exports = env

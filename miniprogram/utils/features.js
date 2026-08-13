// utils/features.js —— 功能开关（前端用）
// 与 config/env.js 的 MONETIZATION_ENABLED 保持一致，供各页面判断是否展示变现相关入口。
// 这样个人主体发布时只需把开关设为 false，会员/积分/邀请等入口即全部隐藏，无需删代码。

const env = require('../config/env')

module.exports = {
  // 是否启用变现（会员/积分/分销佣金）。个人主体发布时应为 false。
  monetizationEnabled: !!(env && env.MONETIZATION_ENABLED)
}

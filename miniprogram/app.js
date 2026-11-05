// app.js —— 知途 AI 旅行小程序入口
const storage = require('./utils/storage')
const { track } = require('./utils/track')

// 从启动参数里取邀请码。冷启动走 onLaunch，热启动（小程序已在后台时点分享链接）
// 只会走 onShow——只在 onLaunch 里读的话，热启动进来的邀请码会静默丢失，
// 分销绑定就一直不生效。
function captureInviteCode(options) {
  const code = options && options.query && options.query.invite_code
  if (code) storage.setBindInvite(code)
}

App({
  globalData: {
    userInfo: null,
    token: '',
    isVip: false,
    city: '杭州'
  },

  onLaunch(options) {
    const token = wx.getStorageSync('token')
    if (token) {
      this.globalData.token = token
      this.globalData.userInfo = wx.getStorageSync('userInfo') || null
      this.globalData.isVip = wx.getStorageSync('isVip') || false
    }
    const city = wx.getStorageSync('city')
    if (city) this.globalData.city = city

    captureInviteCode(options)

    // 启动埋点
    track('app_launch', { hasToken: !!token, city: this.globalData.city })
  },

  onShow(options) {
    captureInviteCode(options)
  }
})

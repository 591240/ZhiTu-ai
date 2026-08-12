// app.js —— 知途 AI 旅行小程序入口
const storage = require('./utils/storage')
const { track } = require('./utils/track')

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

    // 通过分享/扫码进入时，携带的邀请码记录下来，登录后自动绑定
    const inviteCode = options && options.query && options.query.invite_code
    if (inviteCode) storage.setBindInvite(inviteCode)

    // 启动埋点
    track('app_launch', { hasToken: !!token, city: this.globalData.city })
  }
})

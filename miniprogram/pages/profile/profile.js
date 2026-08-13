const { request } = require('../../utils/request')
const storage = require('../../utils/storage')
const auth = require('../../utils/auth')
const { monetizationEnabled } = require('../../utils/features')
const app = getApp()

Page({
  data: {
    user: {},
    stats: { tripCount: 0, cityCount: 0 },
    isVip: false,
    monetization: monetizationEnabled
  },

  onShow() {
    if (!auth.isLogin()) {
      wx.reLaunch({ url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/profile/profile') })
      return
    }
    this.setData({
      user: storage.getUser() || app.globalData.userInfo || {},
      isVip: storage.getIsVip(),
      monetization: monetizationEnabled
    })
    this.loadStats()
    this.loadMe()
    this.bindIfNeeded()
  },

  async bindIfNeeded() {
    const code = storage.getBindInvite()
    if (!code) return
    try {
      const r = await request({ url: '/api/distribution/bind', method: 'POST', data: { invite_code: code } })
      if (r.code === 0) {
        storage.setBindInvite('')  // 绑定成功，清除待绑定码
        wx.showToast({ title: '已通过邀请码绑定', icon: 'none' })
      }
    } catch (e) {}
  },

  async loadMe() {
    try {
      const r = await request({ url: '/api/user/me' })
      if (r.code === 0 && r.data) {
        storage.setUser(r.data)
        app.globalData.userInfo = r.data
        this.setData({ user: r.data, isVip: r.data.is_vip })
      }
    } catch (e) {}
  },

  async updateProfile(payload) {
    try {
      const r = await request({ url: '/api/user/profile', method: 'POST', data: payload })
      if (r.code === 0 && r.data) {
        storage.setUser(r.data)
        app.globalData.userInfo = r.data
        this.setData({ user: r.data })
      }
    } catch (e) {
      wx.showToast({ title: '更新失败', icon: 'none' })
    }
  },

  onChooseAvatar(e) {
    const url = e.detail.avatarUrl
    if (!url) return
    // 先本地立即更新，用户立刻看到变化；再同步后端/存储
    const user = { ...this.data.user, avatar: url }
    this.setData({ user })
    storage.setUser(user)
    app.globalData.userInfo = user
    this.updateProfile({ avatar: url })
  },

  onNicknameChange(e) {
    const nickname = e.detail.value
    if (nickname && nickname !== this.data.user.nickname) {
      this.updateProfile({ nickname })
    }
  },

  async loadStats() {
    try {
      const r = await request({ url: '/api/user/stats' })
      this.setData({ stats: r.data })
    } catch (e) {}
  },

  goMember() { wx.navigateTo({ url: '/pages/member/member' }) },
  goCollection() { wx.navigateTo({ url: '/pages/collection/collection' }) },
  goPublished() { wx.navigateTo({ url: '/pages/published/published' }) },
  goSettings() { wx.navigateTo({ url: '/pages/settings/settings' }) },
  goInvite() { wx.showToast({ title: '邀请功能暂未开放', icon: 'none' }) },
  onShare() { wx.showToast({ title: '分享功能开发中', icon: 'none' }) },
  onService() { wx.showToast({ title: '客服功能开发中', icon: 'none' }) }
})

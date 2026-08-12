const { request } = require('../../utils/request')
const storage = require('../../utils/storage')
const auth = require('../../utils/auth')
const app = getApp()

Page({
  data: {
    user: {},
    stats: { tripCount: 0, cityCount: 0 },
    isVip: false
  },

  onShow() {
    if (!auth.isLogin()) {
      wx.reLaunch({ url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/profile/profile') })
      return
    }
    this.setData({
      user: storage.getUser() || app.globalData.userInfo || {},
      isVip: storage.getIsVip()
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
    if (url) this.updateProfile({ avatar: url })
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
  goInvite() { wx.navigateTo({ url: '/pages/invite/invite' }) },
  onShare() { wx.showToast({ title: '分享功能开发中', icon: 'none' }) },
  onService() { wx.showToast({ title: '客服功能开发中', icon: 'none' }) },
  async onBindPhone(e) {
    const { errMsg, code: phoneCode } = e.detail
    if (errMsg !== 'getPhoneNumber:ok' || !phoneCode) {
      wx.showToast({ title: '已取消', icon: 'none' })
      return
    }
    try {
      const phone = await auth.bindPhone(phoneCode)
      const user = Object.assign({}, this.data.user, { phone })
      this.setData({ user })
      wx.showToast({ title: '绑定成功', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: '绑定失败，请重试', icon: 'none' })
    }
  }
})

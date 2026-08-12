const auth = require('../../utils/auth')
const storage = require('../../utils/storage')
const { request } = require('../../utils/request')

Page({
  data: {
    avatar: '',
    nickname: '',
    redirect: '/pages/index/index'
  },

  onLoad(options) {
    this.setData({ redirect: options.redirect || '/pages/index/index' })
  },

  // 选择微信头像（微信头像来源）
  onChooseAvatar(e) {
    this.setData({ avatar: e.detail.avatarUrl })
  },

  onNicknameBlur(e) {
    this.setData({ nickname: e.detail.value })
  },

  // 保存头像 / 昵称（选填）
  async saveProfile() {
    const { avatar, nickname } = this.data
    if (!avatar && !nickname) return
    try {
      const r = await request({ url: '/api/user/profile', method: 'POST', data: { avatar, nickname } })
      if (r.code === 0 && r.data) {
        storage.setUser(r.data)
        const app = getApp()
        if (app) app.globalData.userInfo = r.data
      }
    } catch (e) {
      // 头像昵称保存失败不影响手机号绑定
    }
  },

  // 微信手机号一键绑定
  async onGetPhone(e) {
    const { errMsg, code: phoneCode } = e.detail
    if (errMsg !== 'getPhoneNumber:ok' || !phoneCode) {
      wx.showToast({ title: '已取消授权', icon: 'none' })
      return
    }
    wx.showLoading({ title: '绑定中' })
    try {
      await this.saveProfile()
      await auth.bindPhone(phoneCode)
      wx.hideLoading()
      wx.showToast({ title: '绑定成功', icon: 'success' })
      this.goHome()
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '绑定失败，请重试', icon: 'none' })
    }
  },

  onSkip() {
    this.goHome()
  },

  goHome() {
    const target = this.data.redirect
    setTimeout(() => {
      wx.reLaunch({
        url: target,
        fail: () => wx.switchTab({ url: '/pages/index/index' })
      })
    }, 300)
  }
})

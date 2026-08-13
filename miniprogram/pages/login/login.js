const auth = require('../../utils/auth')
const { monetizationEnabled } = require('../../utils/features')

Page({
  data: {
    statusBarHeight: 20,
    agreement: true,
    loading: false,
    monetization: monetizationEnabled,
    showPrivacy: false,
    privacyContractName: '《隐私政策》'
  },

  onLoad() {
    const info = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
    this.setData({ statusBarHeight: info.statusBarHeight || 20 })
    // 微信隐私授权：仅当微信侧要求授权时才弹出（个人主体上架必需）
    if (wx.getPrivacySetting) {
      wx.getPrivacySetting({
        success: (res) => {
          if (res.needAuthorization) {
            this.setData({
              showPrivacy: true,
              privacyContractName: res.privacyContractName || '《隐私政策》'
            })
          }
        },
        fail: () => {}
      })
    }
  },

  openPrivacyContract() {
    wx.openPrivacyContract({ fail: () => wx.showToast({ title: '打开失败', icon: 'none' }) })
  },

  onAgreePrivacy() {
    wx.requirePrivacyAuthorize({
      success: () => this.setData({ showPrivacy: false }),
      fail: () => {}
    })
  },

  onRefusePrivacy() {
    wx.showToast({ title: '需同意隐私政策后使用', icon: 'none' })
  },

  toggleAgree() {
    this.setData({ agreement: !this.data.agreement })
  },

  // 跳转到手机号验证码登录页（次要入口）
  goPhoneLogin() {
    wx.navigateTo({ url: '/pages/phone-login/phone-login' })
  },

  // 微信登录（微信号登录）：先拿 openid + token，不绑定手机号
  async onWechatLogin() {
    if (!this.data.agreement) {
      wx.showToast({ title: '请先同意协议', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    try {
      const payload = await auth.login() // 纯微信登录，不带手机号
      this.afterLogin(payload)
    } catch (e) {
      console.error('微信登录失败', e)
      // 透传后端真实错误，优先展示 message；超长时截断避免 toast 显示异常
      const msg = (e && (e.message || e.msg)) || (e && e.data && e.data.message) || '登录失败，请重试'
      wx.showToast({ title: String(msg).slice(0, 30), icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  afterLogin(payload) {
    wx.showToast({ title: '登录成功', icon: 'success' })
    const redirect = (this.options && this.options.redirect) || '/pages/index/index'
    // 未绑定手机号 -> 仅开启变现（非个人主体）时跳转绑定页；个人主体不强制绑手机
    if (monetizationEnabled && !payload.user.phone) {
      setTimeout(() => {
        wx.redirectTo({ url: '/pages/bind-phone/bind-phone?redirect=' + encodeURIComponent(redirect) })
      }, 500)
      return
    }
    setTimeout(() => {
      wx.reLaunch({
        url: redirect,
        fail: () => {
          wx.switchTab({ url: '/pages/index/index' })
        }
      })
    }, 500)
  }
})

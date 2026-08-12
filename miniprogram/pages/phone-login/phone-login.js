const auth = require('../../utils/auth')
const { request } = require('../../utils/request')

function validatePhone(p) {
  return /^1[3-9]\d{9}$/.test(p)
}

Page({
  data: {
    statusBarHeight: 20,
    phone: '',
    code: '',
    counting: 0,        // 倒计时秒数，>0 时禁用获取按钮
    loading: false,
    agreement: true,
    devTip: ''          // 开发模式返回的验证码提示（未配短信 key 时）
  },

  onLoad() {
    const info = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
    this.setData({ statusBarHeight: info.statusBarHeight || 20 })
  },

  onUnload() {
    if (this._timer) clearInterval(this._timer)
  },

  onPhoneInput(e) { this.setData({ phone: e.detail.value }) },
  onCodeInput(e) { this.setData({ code: e.detail.value }) },
  toggleAgree() { this.setData({ agreement: !this.data.agreement }) },

  goBack() {
    const pages = getCurrentPages()
    if (pages.length > 1) wx.navigateBack()
    else wx.redirectTo({ url: '/pages/login/login' })
  },

  async sendCode() {
    const phone = this.data.phone.trim()
    if (!validatePhone(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }
    if (this.data.counting > 0) return
    this.setData({ loading: true })
    try {
      const r = await request({ url: '/api/sms/send', method: 'POST', data: { phone } })
      const dev = r.data && r.data.dev_code
      if (dev) {
        this.setData({ devTip: `开发模式验证码：${dev}（配置短信服务后改为短信发送）` })
      } else {
        this.setData({ devTip: '' })
      }
      wx.showToast({ title: '验证码已发送', icon: 'success' })
      this.startCountdown()
    } catch (e) {
      wx.showToast({ title: (e && e.message) || '发送失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  startCountdown() {
    let left = 60
    this.setData({ counting: left })
    this._timer = setInterval(() => {
      left -= 1
      if (left <= 0) {
        clearInterval(this._timer)
        this._timer = null
        this.setData({ counting: 0 })
      } else {
        this.setData({ counting: left })
      }
    }, 1000)
  },

  async doLogin() {
    const phone = this.data.phone.trim()
    const code = this.data.code.trim()
    if (!validatePhone(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' }); return
    }
    if (!code) {
      wx.showToast({ title: '请输入验证码', icon: 'none' }); return
    }
    if (!this.data.agreement) {
      wx.showToast({ title: '请先同意协议', icon: 'none' }); return
    }
    this.setData({ loading: true })
    try {
      const payload = await auth.phoneLogin(phone, code)
      this.afterLogin(payload)
    } catch (e) {
      console.error('手机号登录失败', e)
      wx.showToast({ title: '登录失败，请重试', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  afterLogin() {
    wx.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(() => {
      wx.reLaunch({ url: '/pages/index/index', fail: () => wx.switchTab({ url: '/pages/index/index' }) })
    }, 500)
  }
})

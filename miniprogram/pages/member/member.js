const { request } = require('../../utils/request')
const storage = require('../../utils/storage')
const { track } = require('../../utils/track')

Page({
  data: {
    isVip: false,
    vipExpireAt: null,
    expireText: '',
    plans: [],
    selectedType: 'year'
  },

  async onLoad() {
    // VIP 状态直接读本地登录态，无需再请求
    const u = storage.getUser() || {}
    this.setData({
      isVip: storage.getIsVip(),
      vipExpireAt: u.vipExpireAt || null,
      expireText: u.vipExpireAt ? this.fmt(u.vipExpireAt) : ''
    })
    try {
      const r = await request({ url: '/api/membership/plans' })
      this.setData({ plans: r.data.plans || [] })
    } catch (e) {}
  },

  fmt(ts) {
    const d = new Date(ts)
    const p = n => (n < 10 ? '0' + n : '' + n)
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate())
  },

  selectPlan(e) { this.setData({ selectedType: e.currentTarget.dataset.t }) },

  async onSubscribe() {
    if (this.data.isVip) return
    wx.showLoading({ title: '开通中' })
    try {
      const r = await request({
        url: '/api/membership/order',
        method: 'POST',
        data: { plan_type: this.data.selectedType, invite_code: storage.getBindInvite() }
      })
      track('member_subscribe', { plan_type: this.data.selectedType })
      this.setData({ isVip: true, vipExpireAt: r.data.vipExpireAt, expireText: this.fmt(r.data.vipExpireAt) })
      wx.hideLoading()
      wx.showToast({ title: '开通成功（演示）', icon: 'success' })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '开通失败', icon: 'none' })
    }
  }
})

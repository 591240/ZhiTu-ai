const { request } = require('../../utils/request')
const storage = require('../../utils/storage')
const { track } = require('../../utils/track')

Page({
  data: {
    points: 0,
    costPerPlan: 10,
    costPerChat: 2,
    plans: [
      { amount: 10, points: 100, note: '体验装' },
      { amount: 30, points: 350, note: '划算', tag: '推荐' },
      { amount: 50, points: 600, note: '超值' }
    ],
    selectedAmount: 30,
    amount: '',
    contact: '',
    note: '',
    submitting: false
  },

  onLoad() {
    const u = storage.getUser() || {}
    this.setData({ points: u.points || 0 })
    this.loadPoints()
  },

  async loadPoints() {
    try {
      const r = await request({ url: '/api/user/points' })
      if (r.code === 0 && r.data) {
        this.setData({ points: r.data.points })
        const user = Object.assign({}, storage.getUser() || {}, { points: r.data.points })
        storage.setUser(user)
      }
    } catch (e) {}
  },

  selectPlan(e) {
    const amount = parseFloat(e.currentTarget.dataset.amount)
    this.setData({ selectedAmount: amount, amount: String(amount) })
  },

  onAmount(e) { this.setData({ amount: e.detail.value }) },
  onContact(e) { this.setData({ contact: e.detail.value }) },
  onNote(e) { this.setData({ note: e.detail.value }) },

  async onSubmit() {
    const amount = parseFloat(this.data.amount)
    if (!amount || amount <= 0) {
      wx.showToast({ title: '请输入充值金额', icon: 'none' })
      return
    }
    if (!this.data.contact.trim()) {
      wx.showToast({ title: '请填写联系方式', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    try {
      await request({
        url: '/api/user/recharge',
        method: 'POST',
        data: {
          amount,
          contact: this.data.contact.trim(),
          note: this.data.note.trim()
        }
      })
      track('points_recharge_apply', { amount })
      wx.showModal({
        title: '申请已提交',
        content: '请添加客服微信并发送支付截图，客服确认后将为您充值积分。',
        showCancel: false,
        confirmText: '知道了'
      })
    } catch (e) {
      wx.showToast({ title: '提交失败，请重试', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})

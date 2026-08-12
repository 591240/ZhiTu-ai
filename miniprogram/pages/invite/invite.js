const { request } = require('../../utils/request')

Page({
  data: {
    invite_code: '',
    invited_count: 0,
    commission_total: 0,
    commission_rate: 0.3,
    records: []
  },

  async onShow() {
    try {
      const r = await request({ url: '/api/distribution/my' })
      if (r.code === 0 && r.data) {
        this.setData({
          invite_code: r.data.invite_code,
          invited_count: r.data.invited_count,
          commission_total: r.data.commission_total,
          commission_rate: r.data.commission_rate,
          records: r.data.records || []
        })
      }
    } catch (e) {}
  },

  copyCode() {
    if (!this.data.invite_code) return
    wx.setClipboardData({
      data: this.data.invite_code,
      success: () => wx.showToast({ title: '邀请码已复制', icon: 'success' })
    })
  },

  onShareAppMessage() {
    const code = this.data.invite_code
    return {
      title: '知途 AI 旅行 — 一键生成你的专属行程',
      path: '/pages/index/index?invite_code=' + code
    }
  }
})

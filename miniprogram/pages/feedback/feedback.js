const { request } = require('../../utils/request')

Page({
  data: {
    content: '',
    contact: ''
  },

  onContent(e) { this.setData({ content: e.detail.value }) },
  onContact(e) { this.setData({ contact: e.detail.value }) },

  async submit() {
    const { content, contact } = this.data
    if (!content.trim()) {
      wx.showToast({ title: '请填写反馈内容', icon: 'none' })
      return
    }
    wx.showLoading({ title: '提交中' })
    try {
      const r = await request({
        url: '/api/user/feedback',
        method: 'POST',
        data: { content: content.trim(), contact: contact.trim() }
      })
      wx.hideLoading()
      if (r.code === 0) {
        wx.showToast({ title: '提交成功', icon: 'success' })
        setTimeout(() => wx.navigateBack(), 800)
      } else {
        wx.showToast({ title: r.message || '提交失败', icon: 'none' })
      }
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '提交失败', icon: 'none' })
    }
  }
})

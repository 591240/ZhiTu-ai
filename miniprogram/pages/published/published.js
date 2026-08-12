const { request } = require('../../utils/request')

Page({
  data: {
    list: [],
    loading: true
  },

  async onLoad() {
    try {
      const r = await request({ url: '/api/template/published' })
      this.setData({ list: r.data.list || [], loading: false })
    } catch (e) {
      this.setData({ loading: false })
    }
  },

  open(e) {
    wx.navigateTo({ url: '/pages/template/template?id=' + e.currentTarget.dataset.id })
  }
})

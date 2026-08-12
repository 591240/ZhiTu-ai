const { request } = require('../../utils/request')
const media = require('../../utils/media')
const app = getApp()

Page({
  data: {
    template: null,
    loading: true,
    collected: false,
    published: false,
    days: []
  },

  async onLoad(options) {
    try {
      const r = await request({ url: '/api/template/detail', data: { id: options.id } })
      const t = r.data.template
      const days = (t.content && t.content.itinerary)
        ? t.content.itinerary.map(d => ({ day: d.day_number, label: d.date_label, count: (d.spots || []).length }))
        : []
      const template = Object.assign({}, t, { image: media.cityImage(t.city) })
      this.setData({ template, days, loading: false })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  async onCollect() {
    if (this.data.collected) return
    try {
      await request({ url: '/api/collection/add', method: 'POST', data: { template_id: this.data.template.id } })
      this.setData({ collected: true })
      wx.showToast({ title: '已收藏', icon: 'success' })
    } catch (e) {}
  },

  async onPublish() {
    if (this.data.published) return
    try {
      await request({ url: '/api/template/publish', method: 'POST', data: { id: this.data.template.id } })
      this.setData({ published: true })
      wx.showToast({ title: '已发布到广场', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: '发布失败', icon: 'none' })
    }
  },

  onUse() {
    const t = this.data.template
    const trip = {
      id: 'fromTpl' + Date.now(),
      title: t.title,
      city: t.city,
      days: t.days,
      route_type: t.route_type,
      content: t.content
    }
    app.globalData.previewTrip = trip
    wx.redirectTo({ url: '/pages/detail/detail?id=preview' })
  }
})

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
    if (!options || !options.id) {
      this.setData({ loading: false })
      wx.showToast({ title: '模板参数缺失', icon: 'none' })
      return
    }
    try {
      const r = await request({ url: '/api/template/detail', data: { id: options.id } })
      const t = r.data.template
      const days = (t.content && t.content.itinerary)
        ? t.content.itinerary.map(d => ({ day: d.day_number, label: d.date_label, count: (d.spots || []).length }))
        : []
      const template = Object.assign({}, t, { image: media.cityImageOnline(t.city) })
      this.setData({ template, days, loading: false })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  onImgError() {
    const t = this.data.template
    if (!t) return
    const fallback = media.cityImageOnlineFallback(t.city)
    if (t.image === fallback) {
      // fallback 也失败，清空 image 让 emoji 兜底显示
      this.setData({ 'template.image': '' })
    } else {
      this.setData({ 'template.image': fallback })
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
      // request 层已经 toast 过后端返回的 message（如「该模板已被其他用户发布」），
      // 这里再盖一层"发布失败"只会把真实原因冲掉
    }
  },

  onUse() {
    const t = this.data.template
    // 不带 id：这是"用模板新建一份行程"，保存时应该新建而不是覆盖模板
    const trip = {
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

const { request } = require('../../utils/request')
const auth = require('../../utils/auth')
const fmt = require('../../utils/format')
const media = require('../../utils/media')

Page({
  data: {
    tab: 'active',
    list: [],
    loading: false
  },

  onShow() {
    if (!auth.isLogin()) {
      wx.reLaunch({ url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/trips/trips') })
      return
    }
    this.loadList()
  },

  switchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab })
    this.loadList()
  },

  async loadList() {
    this.setData({ loading: true })
    try {
      const r = await request({ url: '/api/trip/list', data: { status: this.data.tab } })
      const list = (r.data.list || []).map(t => ({
        ...t,
        title: t.title || '未命名行程',
        city: t.city || '未知城市',
        days: t.days || 1,
        crowd_type: t.crowd_type || '',
        route_type: t.route_type || 'popular',
        total_budget: t.total_budget || 0,
        cover: media.cityEmoji(t.city),
        timeText: fmt.fromNow(t.created_at || Date.now())
      }))
      this.setData({ list, loading: false })
    } catch (e) {
      console.error('加载行程失败', e)
      wx.showToast({ title: '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/detail/detail?id=' + e.currentTarget.dataset.id })
  },

  goPlan() {
    wx.switchTab({ url: '/pages/index/index' })
  },

  onDelete(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '删除行程',
      content: '确定删除该行程？删除后不可恢复。',
      confirmColor: '#FF4D4F',
      success: async (res) => {
        if (res.confirm) {
          await request({ url: '/api/trip/delete', method: 'POST', data: { id } })
          this.loadList()
          wx.showToast({ title: '已删除', icon: 'success' })
        }
      }
    })
  }
})

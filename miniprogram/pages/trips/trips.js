const { request } = require('../../utils/request')
const auth = require('../../utils/auth')
const fmt = require('../../utils/format')
const media = require('../../utils/media')

Page({
  data: {
    tab: 'active',
    list: []
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
    try {
      const r = await request({ url: '/api/trip/list', data: { status: this.data.tab } })
      const list = (r.data.list || []).map(t => ({
        ...t,
        cover: media.cityEmoji(t.city),
        timeText: fmt.fromNow(t.created_at)
      }))
      this.setData({ list })
    } catch (e) {}
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/detail/detail?id=' + e.currentTarget.dataset.id })
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

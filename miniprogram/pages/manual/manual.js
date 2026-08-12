const app = getApp()
const { request } = require('../../utils/request')

const RPX = wx.getWindowInfo().windowWidth / 750
const ITEM_HEIGHT_RPX = 108 // 行高（含 margin）

Page({
  data: {
    title: '',
    city: '杭州',
    days: 2,
    daysArr: [[], []],
    drag: null,          // { di, si, startY, currentY, targetSi }
    dragging: false
  },

  syncDays() {
    const arr = []
    for (let i = 0; i < this.data.days; i++) arr.push([])
    this.setData({ daysArr: arr })
  },

  onTitle(e) { this.setData({ title: e.detail.value }) },
  onCity(e) { this.setData({ city: e.detail.value }) },

  setDays(e) {
    const d = e.currentTarget.dataset.d
    const days = Math.min(Math.max(this.data.days + d, 1), 4)
    this.setData({ days })
    this.syncDays()
  },

  addSpot(e) {
    const di = e.currentTarget.dataset.di
    const daysArr = this.data.daysArr.slice()
    const spots = daysArr[di].slice()
    spots.push({ name: '', time: '', note: '' })
    daysArr[di] = spots
    this.setData({ daysArr })
  },

  updSpot(e) {
    const di = e.currentTarget.dataset.di
    const si = e.currentTarget.dataset.si
    const field = e.currentTarget.dataset.field
    const val = e.detail.value
    const daysArr = this.data.daysArr.slice()
    const spots = daysArr[di].slice()
    spots[si] = Object.assign({}, spots[si], { [field]: val })
    daysArr[di] = spots
    this.setData({ daysArr })
  },

  delSpot(e) {
    const di = e.currentTarget.dataset.di
    const si = e.currentTarget.dataset.si
    const daysArr = this.data.daysArr.slice()
    const spots = daysArr[di].slice()
    spots.splice(si, 1)
    daysArr[di] = spots
    this.setData({ daysArr })
  },

  // 长按开始拖拽
  onDragStart(e) {
    const di = e.currentTarget.dataset.di
    const si = e.currentTarget.dataset.si
    const touch = e.touches[0] || e.changedTouches[0]
    this.setData({
      drag: {
        di,
        si,
        startY: touch.clientY,
        currentY: 0,
        targetSi: si
      },
      dragging: true
    })
    wx.vibrateShort({ type: 'light' })
  },

  onDragMove(e) {
    if (!this.data.drag) return
    const touch = e.touches[0]
    if (!touch) return
    const drag = Object.assign({}, this.data.drag)
    const deltaY = touch.clientY - drag.startY
    const step = Math.round(deltaY / (ITEM_HEIGHT_RPX * RPX))
    const len = this.data.daysArr[drag.di].length
    let targetSi = drag.si + step
    if (targetSi < 0) targetSi = 0
    if (targetSi >= len) targetSi = len - 1
    drag.currentY = deltaY
    drag.targetSi = targetSi
    this.setData({ drag })
  },

  onDragEnd() {
    const drag = this.data.drag
    if (!drag) return
    const { di, si, targetSi } = drag
    if (targetSi !== si) {
      const daysArr = this.data.daysArr.slice()
      const spots = daysArr[di].slice()
      const [item] = spots.splice(si, 1)
      spots.splice(targetSi, 0, item)
      daysArr[di] = spots
      this.setData({ daysArr })
    }
    this.setData({ drag: null, dragging: false })
  },

  onSave() {
    const { title, city, days, daysArr } = this.data
    if (!title.trim()) {
      wx.showToast({ title: '请填写行程标题', icon: 'none' })
      return
    }
    const labels = ['一', '二', '三', '四']
    const itinerary = daysArr.map((spots, i) => ({
      day_number: i + 1,
      date_label: labels[i] ? '第' + labels[i] + '天' : '第' + (i + 1) + '天',
      spots: spots.map(s => ({
        name: s.name, time_slot: s.time || '', duration_min: 0, ticket_price: 0, category: '', description: s.note || ''
      })),
      meals: [], transport: [], budget: 0, tips: ''
    }))
    const trip = {
      title: title.trim(),
      city: city.trim() || '未填城市',
      days,
      route_type: 'popular',
      content: { itinerary, total_budget: 0 }
    }
    wx.showLoading({ title: '保存中' })
    request({
      url: '/api/trip/save',
      method: 'POST',
      data: { trip }
    }).then(() => {
      wx.hideLoading()
      wx.showToast({ title: '已保存到我的行程', icon: 'success' })
      setTimeout(() => wx.switchTab({ url: '/pages/trips/trips' }), 600)
    }).catch(() => {
      wx.hideLoading()
      wx.showToast({ title: '保存失败，请重试', icon: 'none' })
    })
  }
})

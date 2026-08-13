const { request } = require('../../utils/request')
const { track } = require('../../utils/track')
const { spotImage, openPlatform, ticketChannels, chooseTicketChannel, openBooking, dealChannels, openTicketChannel, openDealChannel } = require('../../utils/media')
const app = getApp()

// 给缺失 image 的景点补上封面图（覆盖后端真实行程）
function decorateTrip(trip) {
  if (!trip || !trip.content || !trip.content.itinerary) return trip
  trip.content.itinerary.forEach((day) => {
    (day.spots || []).forEach((s) => {
      if (!s.image) s.image = spotImage(s.name)
    })
  })
  return trip
}

const SLOTS = ['morning', 'afternoon', 'evening']
const SLOT_LABELS = ['上午', '下午', '晚上']
const MEAL_TYPES = ['breakfast', 'lunch', 'dinner']
const MEAL_LABELS = ['早餐', '午餐', '晚餐']

Page({
  data: {
    trip: null,
    dayIndex: 0,
    transportIndex: 0,
    currentDay: null,
    timeline: [],
    loading: true,
    editing: false,
    originTrip: null,
    SLOTS, SLOT_LABELS, MEAL_TYPES, MEAL_LABELS
  },

  async onLoad(options) {
    this._options = options
    if (options.id === 'preview') {
      this.setData({ trip: decorateTrip(app.globalData.previewTrip), loading: false })
    } else {
      try {
        const r = await request({ url: '/api/trip/detail', data: { id: options.id } })
        this.setData({ trip: decorateTrip(r.data.trip), loading: false })
      } catch (e) {
        this.setData({ loading: false })
      }
    }
    this.syncDay()
  },

  async onShow() {
    const trip = this.data.trip
    if (!trip || this.data.editing) return
    if (typeof trip.id === 'number') {
      try {
        const r = await request({ url: '/api/trip/detail', data: { id: trip.id } })
        this.setData({ trip: decorateTrip(r.data.trip) })
        this.syncDay()
      } catch (e) {}
    } else if (app.globalData.adjustTrip) {
      this.setData({ trip: decorateTrip(app.globalData.adjustTrip) })
      this.syncDay()
    }
  },

  syncDay() {
    const { trip, dayIndex } = this.data
    const list = trip && trip.content && trip.content.itinerary
    const currentDay = list && list[dayIndex] ? list[dayIndex] : null
    const timeline = currentDay ? this.buildTimeline(currentDay) : []
    this.setData({ currentDay, timeline })
  },

  // 把当天景点 + 餐饮按开始时间排序，并在相邻节点间插入交通，组成时间轴
  buildTimeline(day) {
    const nodes = []
    ;(day.spots || []).forEach((s, i) => {
      nodes.push({ kind: 'spot', time: s.start_time || '09:00', name: s.name, data: s, _i: i })
    })
    ;(day.meals || []).forEach((m, i) => {
      const def = m.type === 'breakfast' ? '08:00' : m.type === 'lunch' ? '12:30' : '19:00'
      nodes.push({ kind: 'meal', time: m.start_time || def, name: m.name, data: m, _i: i })
    })
    nodes.sort((a, b) => a.time.localeCompare(b.time))
    const timeline = []
    let prev = '酒店'
    nodes.forEach((n) => {
      if (prev !== n.name) {
        timeline.push({ type: 'transport', from: prev, to: n.name, mode: '地铁', duration_min: 30, cost: 5 })
        prev = n.name
      }
      timeline.push(Object.assign({ type: n.kind }, n))
    })
    if (nodes.length) {
      timeline.push({ type: 'transport', from: prev, to: '酒店', mode: '地铁', duration_min: 30, cost: 5 })
    }
    return timeline
  },

  setDay(e) {
    this.setData({ dayIndex: e.currentTarget.dataset.i })
    this.syncDay()
  },

  setTransport(e) {
    this.setData({ transportIndex: e.currentTarget.dataset.i })
  },

  // 跳转火车票实时查询（预填目的地=行程城市）
  goTicket() {
    const to = (this.data.trip && this.data.trip.city) || ''
    wx.navigateTo({ url: `/pages/ticket/ticket?to=${encodeURIComponent(to)}` })
  },

  // 跳转到导航页（显示距用户距离 + 腾讯地图导航）：景点 + 餐饮一起
  goNavigate() {
    const day = this.data.currentDay
    const spots = (day && day.spots) || []
    const meals = (day && day.meals) || []
    if (!spots.length && !meals.length) {
      wx.showToast({ title: '当天暂无地点', icon: 'none' })
      return
    }
    const names = spots.map((s) => s.name).concat(meals.map((m) => m.name)).join(',')
    const types = spots.map(() => 'spot').concat(meals.map(() => 'meal')).join(',')
    const city = (this.data.trip && this.data.trip.city) || ''
    const dayLabel = (day && day.date_label) || ('第' + (this.data.dayIndex + 1) + '天')
    wx.navigateTo({
      url: `/pages/navig/navig?names=${encodeURIComponent(names)}&types=${encodeURIComponent(types)}&city=${encodeURIComponent(city)}&dayLabel=${encodeURIComponent(dayLabel)}`
    })
  },

  // 餐饮「团购/查低价」：AI 已推荐渠道则直接跳转，否则弹出比价列表
  onMealDeal(e) {
    const { di, mi } = e.currentTarget.dataset
    const meal = this.data.trip.content.itinerary[di].meals[mi]
    if (openDealChannel(meal)) return
    const channels = dealChannels(meal)
    const itemList = channels.map((c) => c.name + ' · ' + c.note)
    wx.showActionSheet({
      itemList,
      success: (res) => chooseTicketChannel(channels[res.tapIndex])
    })
  },

  // 跳第三方平台看该景点的图文/视频攻略
  onSpotMedia(e) {
    const name = e.currentTarget.dataset.name
    openPlatform(name)
  },

  // 门票购票：AI 已推荐渠道则直接跳转该渠道，否则弹出比价列表
  onSpotTicket(e) {
    const { di, si } = e.currentTarget.dataset
    const spot = this.data.trip.content.itinerary[di].spots[si]
    if (openTicketChannel(spot)) return
    const channels = ticketChannels(spot)
    const itemList = channels.map((c) => (c.recommend ? '★ ' + c.name : c.name) + ' · ' + c.note)
    wx.showActionSheet({
      itemList,
      success: (res) => chooseTicketChannel(channels[res.tapIndex])
    })
  },

  // 需预约景点 → 复制官方公众号并引导微信搜索预约
  onSpotBooking(e) {
    const { di, si } = e.currentTarget.dataset
    const spot = this.data.trip.content.itinerary[di].spots[si]
    openBooking(spot)
  },

  // ===== 编辑模式 =====
  enterEdit() {
    if (!this.data.trip) return
    this.setData({
      editing: true,
      originTrip: JSON.parse(JSON.stringify(this.data.trip))
    })
    wx.showToast({ title: '已进入编辑', icon: 'none' })
  },

  cancelEdit() {
    if (this.data.originTrip) {
      this.setData({ trip: JSON.parse(JSON.stringify(this.data.originTrip)), editing: false, originTrip: null })
      this.syncDay()
    } else {
      this.setData({ editing: false })
    }
  },

  async saveEdit() {
    if (!this.data.trip) return
    wx.showLoading({ title: '保存中' })
    try {
      await request({ url: '/api/trip/save', method: 'POST', data: { trip: this.data.trip } })
      track('trip_edit', { tripId: this.data.trip.id || 'preview', city: this.data.trip.city })
      this.setData({ editing: false, originTrip: null })
      wx.hideLoading()
      wx.showToast({ title: '已保存', icon: 'success' })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '保存失败', icon: 'none' })
    }
  },

  editDayField(e) {
    const { di, field } = e.currentTarget.dataset
    const trip = this.data.trip
    trip.content.itinerary[di][field] = e.detail.value
    this.setData({ trip })
    this.syncDay()
  },

  editSpotField(e) {
    const { di, si, field } = e.currentTarget.dataset
    const trip = this.data.trip
    let val = e.detail.value
    if (field === 'duration_min' || field === 'ticket_price') val = Number(val) || 0
    trip.content.itinerary[di].spots[si][field] = val
    this.setData({ trip })
    this.syncDay()
  },

  onSpotSlot(e) {
    const { di, si } = e.currentTarget.dataset
    const trip = this.data.trip
    trip.content.itinerary[di].spots[si].time_slot = SLOTS[e.detail.value]
    this.setData({ trip })
    this.syncDay()
  },

  addSpot(e) {
    const di = e.currentTarget.dataset.di
    const trip = this.data.trip
    trip.content.itinerary[di].spots.push({
      name: '新景点', address: '', time_slot: 'morning',
      duration_min: 120, ticket_price: 0, category: '', description: '', photo_spots: []
    })
    this.setData({ trip })
    this.syncDay()
  },

  delSpot(e) {
    const { di, si } = e.currentTarget.dataset
    const trip = this.data.trip
    trip.content.itinerary[di].spots.splice(si, 1)
    this.setData({ trip })
    this.syncDay()
  },

  editMealField(e) {
    const { di, mi, field } = e.currentTarget.dataset
    const trip = this.data.trip
    let val = e.detail.value
    if (field === 'avg_price') val = Number(val) || 0
    trip.content.itinerary[di].meals[mi][field] = val
    this.setData({ trip })
    this.syncDay()
  },

  onMealType(e) {
    const { di, mi } = e.currentTarget.dataset
    const trip = this.data.trip
    trip.content.itinerary[di].meals[mi].type = MEAL_TYPES[e.detail.value]
    this.setData({ trip })
    this.syncDay()
  },

  addMeal(e) {
    const di = e.currentTarget.dataset.di
    const trip = this.data.trip
    trip.content.itinerary[di].meals.push({ name: '新餐厅', type: 'lunch', avg_price: 80, specialty: '', address: '' })
    this.setData({ trip })
    this.syncDay()
  },

  delMeal(e) {
    const { di, mi } = e.currentTarget.dataset
    const trip = this.data.trip
    trip.content.itinerary[di].meals.splice(mi, 1)
    this.setData({ trip })
    this.syncDay()
  },

  // ===== 原有逻辑 =====
  async onSave() {
    if (!this.data.trip) return
    wx.showLoading({ title: '保存中' })
    try {
      await request({ url: '/api/trip/save', method: 'POST', data: { trip: this.data.trip } })
      track('trip_save', { tripId: this.data.trip.id || 'preview', city: this.data.trip.city })
      wx.hideLoading()
      wx.showToast({ title: '已保存', icon: 'success' })
      setTimeout(() => wx.switchTab({ url: '/pages/trips/trips' }), 600)
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '保存失败', icon: 'none' })
    }
  },

  onAdjust() {
    if (!this.data.trip) return
    app.globalData.adjustTrip = JSON.parse(JSON.stringify(this.data.trip))
    wx.navigateTo({ url: '/pages/chat/chat?mode=adjust' })
  }
})

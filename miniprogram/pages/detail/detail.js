const { request } = require('../../utils/request')
const { track } = require('../../utils/track')
const { spotImage, spotImageFallback, openPlatform, ticketChannels, chooseTicketChannel, openBooking, dealChannels, openTicketChannel, openDealChannel } = require('../../utils/media')
const app = getApp()

// 给缺失 image 的景点补上封面图（覆盖后端真实行程）
function decorateTrip(trip) {
  if (!trip || !trip.content || !trip.content.itinerary) return trip
  const city = trip.city || ''
  trip.content.itinerary.forEach((day) => {
    (day.spots || []).forEach((s) => {
      if (!s.image) s.image = spotImage(s.name, city)
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
      const preview = app.globalData.previewTrip
      // 小程序被系统回收后 globalData 会清空，此时只剩 id=preview 的地址，
      // 直接渲染会是一张空白页——给个明确提示而不是静默空白。
      if (!preview) {
        this.setData({ loading: false })
        wx.showModal({
          title: '行程已失效',
          content: '页面数据已过期，请重新生成一次行程。',
          showCancel: false,
          success: () => wx.navigateBack({ fail: () => wx.switchTab({ url: '/pages/index/index' }) })
        })
        return
      }
      this.setData({ trip: decorateTrip(preview), loading: false })
    } else {
      try {
        const r = await request({ url: '/api/trip/detail', data: { id: options.id } })
        this.setData({ trip: decorateTrip(r.data.trip), loading: false })
      } catch (e) {
        this.setData({ loading: false })
      }
    }
    this.syncDay()
    const t = this.data.trip
    const city = (t && t.city) || ''
    this.setData({ headImage: city ? `/images/cities/${city}.jpg` : '/images/home-journey-hero-v1.jpg' })
  },

  onHeadError() {
    if (this.data.headImage !== '/images/home-journey-hero-v1.jpg') {
      this.setData({ headImage: '/images/home-journey-hero-v1.jpg' })
    }
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
      // 消费即清空：这个字段以前永不清除，导致「微调过一次」之后
      // 所有预览态详情页都被那份旧行程覆盖。
      const adjusted = app.globalData.adjustTrip
      app.globalData.adjustTrip = null
      this.setData({ trip: decorateTrip(adjusted) })
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

  // 把 HH:MM 转成当天分钟数，用于计算时间差
  _minutes(t) {
    const [h, m] = (t || '00:00').split(':').map(Number)
    return h * 60 + m
  },

  // 计算两个字符串的相似度（简单包含/公共子串），用于按地址区域匹配美食
  _textSimilarity(a, b) {
    const x = (a || '').toLowerCase().replace(/[^\u4e00-\u9fa5a-z0-9]/g, '')
    const y = (b || '').toLowerCase().replace(/[^\u4e00-\u9fa5a-z0-9]/g, '')
    if (!x || !y) return 0
    if (x.includes(y) || y.includes(x)) return 1
    // 公共连续子串长度
    let best = 0
    for (let i = 0; i < x.length; i++) {
      for (let j = 0; j < y.length; j++) {
        let k = 0
        while (i + k < x.length && j + k < y.length && x[i + k] === y[j + k]) k++
        if (k > best) best = k
      }
    }
    return best / Math.max(x.length, y.length)
  },

  // 为景点匹配最合适的 meal：优先 spot.nearby_food，其次按 time_slot 类型，再按地址区域，最后按时间最近
  _matchMeal(spot, meals, spotTime) {
    if (!meals || !meals.length) return null
    // 1. 景点自身附带附近美食（后端 AI 生成）
    if (spot && spot.nearby_food && spot.nearby_food.name) {
      return Object.assign({}, spot.nearby_food, { _from: 'nearby' })
    }
    // 2. 按 time_slot 匹配早/午/晚餐类型
    const slot = (spot && spot.time_slot) || ''
    const typeMap = { morning: 'breakfast', afternoon: 'lunch', evening: 'dinner' }
    const targetType = typeMap[slot] || ''
    if (targetType) {
      const byType = meals.filter((m) => m.type === targetType)
      if (byType.length) {
        // 同类型中再按地址区域最近挑
        const spotAddr = (spot && spot.address) || ''
        const scored = byType.map((m) => ({
          m,
          score: this._textSimilarity(spotAddr, m.address || '')
        })).sort((a, b) => b.score - a.score)
        return Object.assign({}, scored[0].m, { _from: 'type' })
      }
    }
    // 3. 按地址区域相似度匹配
    const spotAddr = (spot && spot.address) || ''
    if (spotAddr) {
      const scored = meals.map((m) => ({
        m,
        score: this._textSimilarity(spotAddr, m.address || '')
      })).sort((a, b) => b.score - a.score)
      if (scored[0].score > 0.3) {
        return Object.assign({}, scored[0].m, { _from: 'addr' })
      }
    }
    // 4. 兜底：按时间最近
    const mt = (m) => m.start_time || (m.type === 'breakfast' ? '08:00' : m.type === 'lunch' ? '12:30' : '19:00')
    const sorted = meals.map((m, mi) => ({
      m, mi,
      diff: Math.abs(this._minutes(spotTime) - this._minutes(mt(m)))
    })).sort((a, b) => a.diff - b.diff)
    return sorted.length ? Object.assign({}, sorted[0].m, { _from: 'time' }) : null
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
    let ti = 0
    const transports = day.transport || []
    nodes.forEach((n) => {
      if (prev !== n.name) {
        const t = transports[ti++] || { from: prev, to: n.name, mode: '地铁', duration_min: 30, cost: 5 }
        timeline.push(Object.assign({ type: 'transport' }, t))
        prev = n.name
      }
      timeline.push(Object.assign({ type: n.kind }, n))
    })
    if (nodes.length) {
      const t = transports[ti++] || { from: prev, to: '酒店', mode: '地铁', duration_min: 30, cost: 5 }
      timeline.push(Object.assign({ type: 'transport' }, t))
    }
    // 给每个景点附加「顺路美食」推荐
    const meals = day.meals || []
    timeline.forEach((item) => {
      if (item.type !== 'spot' || !item.data) return
      const firstNearMeal = this._matchMeal(item.data, meals, item.time || '12:00')
      const nearMeals = firstNearMeal ? [firstNearMeal] : []
      const firstPhotoSpot = (item.data.photo_spots && item.data.photo_spots[0]) ? item.data.photo_spots[0] : null
      item.data = Object.assign({}, item.data, { nearMeals, firstNearMeal, firstPhotoSpot })
    })
    // 给每个时间轴节点分配唯一 tid，避免 wx:key="type" 因同类节点重复而报警告
    timeline.forEach((it, idx) => { it.tid = idx })
    return timeline
  },

  setDay(e) {
    this.setData({ dayIndex: e.currentTarget.dataset.i })
    this.syncDay()
  },

  setTransport(e) {
    this.setData({ transportIndex: e.currentTarget.dataset.i })
  },

  // 景点封面图加载失败：先换稳定 fallback，再失败才显示 emoji
  onImgError(e) {
    const ti = e.currentTarget.dataset.ti
    const timeline = this.data.timeline.slice()
    const item = timeline[ti]
    if (!item || !item.data) return
    const name = item.data.name || ''
    const city = (this.data.trip && this.data.trip.city) || ''
    const fallback = spotImageFallback(name, city)
    if (item.data.image === fallback || !fallback) {
      item.data = Object.assign({}, item.data, { _imgError: true })
    } else {
      item.data = Object.assign({}, item.data, { image: fallback })
    }
    timeline[ti] = Object.assign({}, item, { data: item.data })
    this.setData({ timeline })
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
      const r = await request({ url: '/api/trip/save', method: 'POST', data: { trip: this.data.trip } })
      // 必须回写 id：否则再点一次保存就是"新建"，库里会多出一条重复行程，
      // 而且 onShow 的 typeof id === 'number' 永远为假，页面不会刷新。
      const savedId = r.data && r.data.id
      if (savedId) this.setData({ 'trip.id': savedId })
      track('trip_edit', { tripId: savedId || this.data.trip.id || 'preview', city: this.data.trip.city })
      this.setData({ editing: false, originTrip: null })
      wx.hideLoading()
      wx.showToast({ title: '已保存', icon: 'success' })
    } catch (e) {
      wx.hideLoading()
      console.error('保存行程失败', e)
      const msg = (e && (e.message || e.errMsg || e)) || '保存失败'
      wx.showToast({ title: String(msg).slice(0, 60), icon: 'none' })
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
      const r = await request({ url: '/api/trip/save', method: 'POST', data: { trip: this.data.trip } })
      const savedId = r.data && r.data.id
      if (savedId) this.setData({ 'trip.id': savedId })
      track('trip_save', { tripId: savedId || this.data.trip.id || 'preview', city: this.data.trip.city })
      wx.hideLoading()
      wx.showToast({ title: '已保存', icon: 'success' })
      setTimeout(() => wx.switchTab({ url: '/pages/trips/trips' }), 600)
    } catch (e) {
      wx.hideLoading()
      console.error('保存行程失败', e)
      const msg = (e && (e.message || e.errMsg || e)) || '保存失败'
      wx.showToast({ title: String(msg).slice(0, 60), icon: 'none' })
    }
  },

  onAdjust() {
    if (!this.data.trip) return
    app.globalData.adjustTrip = JSON.parse(JSON.stringify(this.data.trip))
    wx.navigateTo({ url: '/pages/chat/chat?mode=adjust' })
  }
})

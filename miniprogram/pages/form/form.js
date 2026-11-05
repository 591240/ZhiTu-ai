const { request } = require('../../utils/request')
const storage = require('../../utils/storage')
const { track } = require('../../utils/track')
const { handleBizError } = require('../../utils/error')
const app = getApp()

const CROWD = ['亲子（大人带小孩）', '情侣', '学生', '中老年', '朋友', '其他']
const PREFS = ['自然风光', '人文历史', '美食探店', '网红打卡', '休闲度假']
const TRANSPORT = ['自驾', '公共交通', '步行', '混合']
const ROUTE = [
  { v: 'popular', label: '大众观光' },
  { v: 'niche', label: '小众深度' }
]
// 往返交通偏好（与市内交通 transport_mode 区分）
const TRANSPORT_PREF = ['高铁优先', '火车出行', '飞机优先', '大巴优先', '性价比优先', '省时优先']

Page({
  data: {
    cities: [],
    city: '杭州',
    days: 2,
    crowdIndex: 1,
    prefs: [],
    mustSee: '',
    transportIndex: 2,
    routeIndex: 0,
    remark: '',
    CROWD, PREFS, TRANSPORT, ROUTE, TRANSPORT_PREF,
    generating: false,
    // —— 新增维度 ——
    departureCity: '',
    startDate: '',
    endDate: '',
    peopleCount: 2,
    transportPrefIndex: 0,
    // 自定义预算（元/人）
    budgetMin: 500,
    budgetMax: 1500
  },

  onLoad() {
    this.setData({ city: storage.getCity() })
  },

  onCityInput(e) { this.setData({ city: e.detail.value }) },
  onDeparture(e) { this.setData({ departureCity: e.detail.value }) },
  setDays(e) {
    const days = Number(e.currentTarget.dataset.d)
    let { startDate, endDate } = this.data
    if (startDate) {
      endDate = this._offsetDate(startDate, days - 1)
    } else if (endDate) {
      startDate = this._offsetDate(endDate, -(days - 1))
    }
    this.setData({ days, startDate, endDate })
  },
  setCrowd(e) { this.setData({ crowdIndex: e.currentTarget.dataset.i }) },
  setTransport(e) { this.setData({ transportIndex: e.currentTarget.dataset.i }) },
  setRoute(e) { this.setData({ routeIndex: e.currentTarget.dataset.i }) },
  setTransportPref(e) { this.setData({ transportPrefIndex: e.currentTarget.dataset.i }) },
  onStart(e) {
    const startDate = e.detail.value
    let { endDate, days } = this.data
    if (endDate) {
      days = this._calcDays(startDate, endDate)
    } else if (startDate) {
      endDate = this._offsetDate(startDate, days - 1)
    }
    this.setData({ startDate, endDate, days })
  },
  onEnd(e) {
    const endDate = e.detail.value
    let { startDate, days } = this.data
    if (startDate) {
      days = this._calcDays(startDate, endDate)
    } else if (endDate) {
      startDate = this._offsetDate(endDate, -(days - 1))
    }
    this.setData({ startDate, endDate, days })
  },
  _calcDays(start, end) {
    const s = new Date(start + 'T00:00:00')
    const e = new Date(end + 'T00:00:00')
    const diff = Math.round((e - s) / (1000 * 60 * 60 * 24)) + 1
    return Math.max(1, Math.min(4, diff))
  },
  _offsetDate(dateStr, offsetDays) {
    const d = new Date(dateStr + 'T00:00:00')
    d.setDate(d.getDate() + offsetDays)
    return this._fmtDate(d)
  },
  _fmtDate(d) {
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  },
  setPeople(e) {
    const delta = Number(e.currentTarget.dataset.d)
    const n = Math.max(1, Math.min(20, this.data.peopleCount + delta))
    this.setData({ peopleCount: n })
  },
  togglePref(e) {
    const p = e.currentTarget.dataset.p
    const prefs = this.data.prefs.slice()
    const idx = prefs.indexOf(p)
    if (idx >= 0) prefs.splice(idx, 1)
    else prefs.push(p)
    this.setData({ prefs })
  },
  onRemark(e) { this.setData({ remark: e.detail.value }) },
  onMustSee(e) { this.setData({ mustSee: e.detail.value }) },
  onBudgetMin(e) {
    const v = parseInt(e.detail.value) || 0
    const budgetMin = Math.max(0, v)
    let { budgetMax } = this.data
    if (budgetMin > budgetMax) budgetMax = budgetMin
    this.setData({ budgetMin, budgetMax })
  },
  onBudgetMax(e) {
    const v = parseInt(e.detail.value) || 0
    let budgetMax = Math.max(0, v)
    const { budgetMin } = this.data
    if (budgetMax < budgetMin) budgetMax = budgetMin
    this.setData({ budgetMax })
  },

  async onGenerate() {
    if (this.data.generating) return
    this.setData({ generating: true })
    wx.showLoading({ title: 'AI 规划中' })
    try {
      const d = this.data
      const r = await request({
        url: '/api/plan/form',
        method: 'POST',
        data: {
          city: d.city,
          days: d.days,
          crowd_type: d.CROWD[d.crowdIndex],
          budget_min: d.budgetMin,
          budget_max: d.budgetMax,
          preferences: d.prefs,
          transport_mode: d.TRANSPORT[d.transportIndex],
          route_type: d.ROUTE[d.routeIndex].v,
          remark: d.remark,
          departure_city: d.departureCity,
          start_date: d.startDate,
          end_date: d.endDate,
          people_count: d.peopleCount,
          transport_preference: d.TRANSPORT_PREF[d.transportPrefIndex],
          must_see: d.mustSee
        }
      })
      app.globalData.previewTrip = r.data.trip
      track('plan_generate', { mode: 'form', city: d.city, days: d.days, route: d.ROUTE[d.routeIndex].v })
      wx.hideLoading()
      wx.redirectTo({ url: '/pages/detail/detail?id=preview' })
    } catch (e) {
      wx.hideLoading()
      if (!handleBizError(e)) {
        wx.showToast({ title: (e && e.message) || '生成失败，请重试', icon: 'none' })
      }
    } finally {
      this.setData({ generating: false })
    }
  }
})

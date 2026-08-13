const { request } = require('../../utils/request')
const storage = require('../../utils/storage')
const mock = require('../../utils/mock')
const { track } = require('../../utils/track')
const app = getApp()

const CROWD = ['亲子（大人带小孩）', '情侣', '学生', '中老年', '朋友', '其他']
const PREFS = ['自然风光', '人文历史', '美食探店', '网红打卡', '休闲度假']
const TRANSPORT = ['自驾', '公共交通', '步行', '混合']
const ROUTE = [
  { v: 'popular', label: '大众观光' },
  { v: 'niche', label: '小众深度' }
]
// 往返交通偏好（与市内交通 transport_mode 区分）
const TRANSPORT_PREF = ['高铁优先', '飞机优先', '大巴优先', '性价比优先', '省时优先']

Page({
  data: {
    cities: [],
    city: '杭州',
    days: 2,
    crowdIndex: 1,
    prefs: [],
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
    this.setData({ cities: mock.mockCities.map(c => c.name), city: storage.getCity() })
  },

  onCity(e) { this.setData({ city: this.data.cities[e.detail.value] }) },
  onDeparture(e) { this.setData({ departureCity: e.detail.value }) },
  setDays(e) { this.setData({ days: e.currentTarget.dataset.d }) },
  setCrowd(e) { this.setData({ crowdIndex: e.currentTarget.dataset.i }) },
  setTransport(e) { this.setData({ transportIndex: e.currentTarget.dataset.i }) },
  setRoute(e) { this.setData({ routeIndex: e.currentTarget.dataset.i }) },
  setTransportPref(e) { this.setData({ transportPrefIndex: e.currentTarget.dataset.i }) },
  onStart(e) { this.setData({ startDate: e.detail.value }) },
  onEnd(e) { this.setData({ endDate: e.detail.value }) },
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
          transport_preference: d.TRANSPORT_PREF[d.transportPrefIndex]
        }
      })
      app.globalData.previewTrip = r.data.trip
      track('plan_generate', { mode: 'form', city: d.city, days: d.days, route: d.ROUTE[d.routeIndex].v })
      wx.hideLoading()
      wx.redirectTo({ url: '/pages/detail/detail?id=preview' })
    } catch (e) {
      wx.hideLoading()
      if (e && e.code === 4001) {
        wx.showModal({
          title: '积分不足',
          content: '本次生成需要 10 积分，您的积分已用完，请前往充值。',
          confirmText: '去充值',
          cancelText: '取消',
          success: (res) => {
            if (res.confirm) wx.navigateTo({ url: '/pages/member/member' })
          }
        })
      } else {
        wx.showToast({ title: '生成失败，请重试', icon: 'none' })
      }
    } finally {
      this.setData({ generating: false })
    }
  }
})

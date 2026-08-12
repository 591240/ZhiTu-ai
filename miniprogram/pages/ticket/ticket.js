const { request } = require('../../utils/request')
const { openLocation, buyOn12306 } = require('../../utils/map')

function pad(n) { return n < 10 ? '0' + n : '' + n }
function defaultDate(offset) {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function weekText(dateStr) {
  const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const d = new Date(dateStr)
  return isNaN(d.getTime()) ? '' : week[d.getDay()]
}
function typeLabel(type) {
  const map = { '': '全部', 'G': '高铁', 'D': '动车', 'K': '普快' }
  return map[type] || '全部'
}

Page({
  data: {
    from: '',
    to: '',
    date: defaultDate(3),
    weekText: '',
    trainType: '',
    typeText: typeLabel(''),
    loading: false,
    result: null
  },

  onLoad(options) {
    const date = this.data.date
    const to = options.to ? decodeURIComponent(options.to) : this.data.to
    this.setData({ to, weekText: weekText(date) })
  },

  onFrom(e) { this.setData({ from: e.detail.value }) },
  onTo(e) { this.setData({ to: e.detail.value }) },
  focusFrom() {},
  focusTo() {},
  onDate(e) {
    const date = e.detail.value
    this.setData({ date, weekText: weekText(date) })
  },
  showTypeSheet() {
    const types = ['全部', '高铁', '动车', '普快']
    const values = ['', 'G', 'D', 'K']
    wx.showActionSheet({
      itemList: types,
      success: (res) => {
        const trainType = values[res.tapIndex]
        this.setData({ trainType, typeText: types[res.tapIndex] })
      }
    })
  },
  swap() {
    const { from, to } = this.data
    this.setData({ from: to, to: from })
  },

  // 从车次原始行中尽力提取出发/到达站，失败回退到用户输入的城市
  extractFrom(line, fallback) {
    if (!line) return fallback
    const byTime = line.match(/([一-龥]{2,8}站?)(?=\s+\d{1,2}:\d{2})/g)
    if (byTime && byTime.length) return byTime[0]
    const stations = line.match(/[一-龥]{2,8}站/g)
    if (stations && stations.length) return stations[0]
    return fallback
  },

  extractDest(line, fallback) {
    if (!line) return fallback
    const byTime = line.match(/([一-龥]{2,8}站?)(?=\s+\d{1,2}:\d{2})/g)
    if (byTime && byTime.length) return byTime[byTime.length - 1]
    const byArrow = line.match(/→\s*([一-龥]{2,8}站?)/)
    if (byArrow) return byArrow[1]
    const stations = line.match(/[一-龥]{2,8}站/g)
    if (stations && stations.length) return stations[stations.length - 1]
    return fallback
  },

  onMap(e) {
    const station = e.currentTarget.dataset.station
    openLocation(station)
  },

  onBuy() {
    const { from, to, date } = this.data
    buyOn12306({ from: from.trim(), to: to.trim(), date })
  },

  async query() {
    const { from, to, date, trainType } = this.data
    if (!from.trim() || !to.trim()) {
      wx.showToast({ title: '请填写出发地和目的地', icon: 'none' })
      return
    }
    if (!date) {
      wx.showToast({ title: '请选择日期', icon: 'none' })
      return
    }
    this.setData({ loading: true, result: null })
    try {
      const params = { date, from_station: from.trim(), to_station: to.trim() }
      if (trainType) params.train_type = trainType
      const r = await request({ url: '/api/ticket/search', data: params })
      const result = r.data || {}
      // 给每张车次预计算出发/到达站，用于展示
      if (result.trains && result.trains.length) {
        result.trains = result.trains.map(t => ({
          ...t,
          fromStation: this.extractFrom(t.line, from.trim()),
          toStation: this.extractDest(t.line, to.trim())
        }))
      }
      this.setData({ result, loading: false })
    } catch (e) {
      this.setData({ loading: false })
      const msg = (e && (e.message || e.msg || (typeof e === 'string' ? e : '查询失败'))) || '查询失败'
      wx.showToast({ title: msg, icon: 'none' })
    }
  }
})

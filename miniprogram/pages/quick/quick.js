const { request } = require('../../utils/request')
const { track } = require('../../utils/track')
const app = getApp()

const COMMON_CITIES = ['北京','上海','广州','深圳','武汉','青岛','大理','丽江','三亚','天津','昆明','桂林','长沙','南京','厦门','重庆','西安','苏州','杭州','成都']

Page({
  data: {
    text: '',
    examples: ['带爸妈杭州2日轻松游', '成都3天小众美食之旅', '西安2日历史美食游', '重庆2日网红打卡', '苏州1日园林游'],
    parsed: null,
    generating: false
  },

  parse(text) {
    const t = (text || '').toLowerCase()
    let city = '杭州'
    for (const c of COMMON_CITIES) {
      if (t.indexOf(c.toLowerCase()) >= 0) { city = c; break }
    }
    const m = text && text.match(/(\d+)\s*[天日]/)
    const days = m ? Math.min(Math.max(parseInt(m[1], 10), 1), 4) : 2
    const niche = /小众|深度|文艺|冷门|秘境|quiet/i.test(text || '')
    const route_type = niche ? 'niche' : 'popular'
    const routeLabel = niche ? '小众深度' : '大众经典'
    let crowd_type = ''
    if (/爸妈|父母|老人|中老年/.test(text || '')) crowd_type = '中老年'
    else if (/情侣|对象|另一半|老婆|老公/.test(text || '')) crowd_type = '情侣'
    else if (/亲子|小孩|孩子|宝宝|带娃/.test(text || '')) crowd_type = '亲子'
    else if (/朋友|闺蜜|兄弟|哥们/.test(text || '')) crowd_type = '朋友'
    else if (/学生|同学/.test(text || '')) crowd_type = '学生'
    return { city, days, route_type, routeLabel, crowd_type }
  },

  onInput(e) {
    this.setData({ text: e.detail.value })
    this.setData({ parsed: this.data.text.trim() ? this.parse(this.data.text) : null })
  },

  onExample(e) {
    this.setData({ text: e.currentTarget.dataset.text })
    this.setData({ parsed: this.parse(e.currentTarget.dataset.text) })
  },

  async onGenerate() {
    const text = this.data.text.trim()
    if (!text || this.data.generating) return
    const p = this.parse(text)
    this.setData({ generating: true })
    wx.showLoading({ title: 'AI 规划中' })
    try {
      const r = await request({
        url: '/api/plan/quick',
        method: 'POST',
        data: { text, city: p.city, days: p.days, route_type: p.route_type, crowd_type: p.crowd_type }
      })
      app.globalData.previewTrip = r.data.trip
      track('plan_generate', { mode: 'quick', city: p.city, days: p.days, route: p.route_type })
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

const { request, streamRequest } = require('../../utils/request')
const app = getApp()

Page({
  data: {
    activeTab: 0,
    messages: [],
    input: '',
    sending: false,
    lastId: '',
    quickQs: ['西湖几点开门？', '成都有什么必吃美食？', '带娃出游行李清单', '有哪些避坑建议？'],
    luggage: [],
    food: { red: [], black: [] },
    // —— 行程对话微调模式 ——
    mode: '',            // 'adjust' 时为行程微调模式
    adjustTrip: null,    // 当前正在微调的行程
    adjusted: false      // 是否已发生过一次微调（用于显示保存按钮）
  },

  onLoad(options) {
    if (options && options.mode === 'adjust') {
      const trip = app.globalData.adjustTrip || null
      this.setData({
        mode: 'adjust',
        adjustTrip: trip,
        activeTab: 0,
        messages: trip ? [{
          role: 'ai',
          text: `已进入「${trip.title || trip.city || '行程'}」的对话微调。直接告诉我你想怎么改，例如：「把第二天的西湖换成灵隐寺」「第一天加一顿本地晚餐」「行程节奏再轻松点」。`
        }] : []
      })
    }
  },

  onTab(e) {
    const i = parseInt(e.currentTarget.dataset.i, 10)
    this.setData({ activeTab: i })
    if (i === 1 && this.data.luggage.length === 0) this.loadLuggage()
    if (i === 2 && this.data.food.red.length === 0) this.loadFood()
  },

  onInput(e) { this.setData({ input: e.detail.value }) },

  onQuick(e) {
    this.setData({ input: e.currentTarget.dataset.q })
    this.send()
  },

  async send() {
    const q = this.data.input.trim()
    if (!q || this.data.sending) return
    const messages = this.data.messages.concat([{ role: 'user', text: q }, { role: 'ai', text: '' }])
    const aiIndex = messages.length - 1
    this.setData({ messages, input: '', sending: true, lastId: 'm' + aiIndex })

    try {
      if (this.data.mode === 'adjust') {
        await this._adjustSend(q, messages)
      } else {
        const that = this
        streamRequest('/api/chat/qa', { question: q },
          (chunk) => {
            const msgs = that.data.messages.slice()
            msgs[aiIndex] = { role: 'ai', text: (msgs[aiIndex].text || '') + chunk }
            that.setData({ messages: msgs, lastId: 'm' + aiIndex })
          },
          () => { that.setData({ sending: false }) }
        )
      }
    } catch (e) {
      const msgs = this.data.messages.slice()
      msgs[aiIndex] = { role: 'ai', text: '抱歉，我暂时无法处理，请稍后再试。' }
      this.setData({ messages: msgs, sending: false })
    }
  },

  async _adjustSend(q, messages) {
    const r = await request({
      url: '/api/plan/chat-adjust',
      method: 'POST',
      data: { trip: this.data.adjustTrip, instruction: q }
    })
    const newTrip = r.data.trip
    const reply = r.data.reply || '已为你调整行程。'
    app.globalData.adjustTrip = newTrip
    const msgs = messages.concat([{ role: 'ai', text: reply }])
    this.setData({
      messages: msgs,
      lastId: 'm' + (msgs.length - 1),
      adjustTrip: newTrip,
      adjusted: true,
      sending: false
    })
  },

  async saveAdjust() {
    if (!this.data.adjustTrip) return
    wx.showLoading({ title: '保存中' })
    try {
      const r = await request({ url: '/api/trip/save', method: 'POST', data: { trip: this.data.adjustTrip } })
      wx.hideLoading()
      // 若原来是预览态（无数字 id），保存后拿到真实 id，回写全局副本
      const savedId = r.data && r.data.id
      if (savedId && typeof this.data.adjustTrip.id !== 'number') {
        app.globalData.adjustTrip = Object.assign({}, this.data.adjustTrip, { id: savedId })
      }
      wx.showToast({ title: '已保存行程', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 600)
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '保存失败', icon: 'none' })
    }
  },

  async loadLuggage() {
    try {
      const r = await request({ url: '/api/chat/luggage', method: 'POST', data: {} })
      const luggage = (r.data.list || []).map(g => ({ group: g.group, items: g.items.map(n => ({ name: n, done: false })) }))
      this.setData({ luggage })
    } catch (e) {}
  },

  async loadFood() {
    try {
      const r = await request({ url: '/api/chat/food', method: 'POST', data: { city: '' } })
      this.setData({ food: { red: r.data.red || [], black: r.data.black || [] } })
    } catch (e) {}
  },

  toggleLuggage(e) {
    const gi = parseInt(e.currentTarget.dataset.gi, 10)
    const ii = parseInt(e.currentTarget.dataset.ii, 10)
    const luggage = this.data.luggage.slice()
    const items = luggage[gi].items.slice()
    items[ii] = Object.assign({}, items[ii], { done: !items[ii].done })
    luggage[gi] = Object.assign({}, luggage[gi], { items })
    this.setData({ luggage })
  }
})

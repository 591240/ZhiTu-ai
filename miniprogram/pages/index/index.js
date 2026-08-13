const env = require('../../config/env')
const { request } = require('../../utils/request')
const storage = require('../../utils/storage')
const mock = require('../../utils/mock')
const auth = require('../../utils/auth')
const media = require('../../utils/media')

Page({
  data: {
    city: '杭州',
    cityNames: [],
    cityIndex: 0,
    services: [
      { key: 'map', name: '导航' },
      { key: 'car', name: '打车' },
      { key: 'hotel', name: '酒店' },
      { key: 'food', name: '美食' },
      { key: 'flight', name: '机票高铁' },
      { key: 'ticket', name: '景区门票' },
      { key: 'movie', name: '电影票' },
      { key: 'takeout', name: '外卖' }
    ],
    templates: [],
    tplAnimate: false,
    statusBarHeight: 20,
    navHeight: 44
  },

  onLoad() {
    const info = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
    const city = storage.getCity() || '杭州'
    const cityNames = mock.mockCities.map(c => c.name)
    const cityIndex = Math.max(0, cityNames.indexOf(city))
    this.setData({
      city,
      cityNames,
      cityIndex,
      statusBarHeight: info.statusBarHeight || 20,
      navHeight: 44
    })
    this.loadTemplates()
  },

  onShow() {
    if (!auth.isLogin()) {
      wx.reLaunch({ url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/index/index') })
      return
    }
    const city = storage.getCity() || '杭州'
    const cityIndex = Math.max(0, this.data.cityNames.indexOf(city))
    this.setData({ city, cityIndex })
  },

  async loadTemplates() {
    try {
      const r = await request({ url: '/api/template/hot' })
      const list = (r.data.list || []).map(t => ({
        ...t,
        image: media.cityImage(t.city),
        hot: (t.uses || 0) >= 80
      }))
      this.setData({ templates: list })
    } catch (e) {}
  },

  onPickCity() {
    const cities = mock.mockCities.map(c => c.name)
    wx.showActionSheet({
      itemList: cities,
      success: (res) => {
        const city = cities[res.tapIndex]
        storage.setCity(city)
        this.setData({ city })
        getApp().globalData.city = city
      }
    })
  },

  goForm() { wx.navigateTo({ url: '/pages/form/form' }) },
  goQuick() { wx.navigateTo({ url: '/pages/quick/quick' }) },
  goOcr() { wx.navigateTo({ url: '/pages/ocr/ocr' }) },
  goManual() { wx.navigateTo({ url: '/pages/manual/manual' }) },
  goChat() { wx.navigateTo({ url: '/pages/chat/chat' }) },
  goTemplate(e) { wx.navigateTo({ url: '/pages/template/template?id=' + e.currentTarget.dataset.id }) },

  onService(e) {
    const key = e.currentTarget.dataset.key
    const link = env.SERVICE_LINKS[key]
    const name = (link && link.name) || e.currentTarget.dataset.name
    if (!link || !link.appId) {
      wx.showToast({ title: '该服务暂未配置跳转', icon: 'none' })
      return
    }
    if (env.USE_MOCK) {
      wx.showToast({ title: '演示版将跳转：' + name, icon: 'none' })
      return
    }
    wx.navigateToMiniProgram({
      appId: link.appId,
      extraData: { city: this.data.city },
      fail: () => wx.showToast({ title: '跳转' + name + '失败，请检查白名单', icon: 'none' })
    })
  },

  onRefreshTpl() {
    this.setData({ tplAnimate: false })
    setTimeout(() => {
      const arr = this.data.templates.slice()
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[arr[i], arr[j]] = [arr[j], arr[i]]
      }
      this.setData({ templates: arr, tplAnimate: true })
    }, 100)
  },

  // 模板封面图加载失败时：本地图不存在 -> 尝试在线关键词图 -> 再回退 emoji
  onImgError(e) {
    const idx = e.currentTarget.dataset.index
    const t = this.data.templates[idx]
    const current = t.image || ''
    if (current.startsWith('/images/cities/')) {
      this.setData({ [`templates[${idx}].image`]: media.cityImageOnline(t.city) })
    } else {
      this.setData({ [`templates[${idx}].image`]: '' })
    }
  }
})

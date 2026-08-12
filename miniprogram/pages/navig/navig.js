const { request } = require('../../utils/request')
const { openMultiMap, haversineKm } = require('../../utils/map')
const { spotImage } = require('../../utils/media')

const MEAL_EMOJI = { breakfast: '🥢', lunch: '🍜', dinner: '🍲', default: '🍽' }

Page({
  data: {
    city: '',
    dayLabel: '',
    myLat: null,
    myLng: null,
    locs: [],        // [{name, address, lat, lng, distance, type, image, emoji}]
    loading: true,
    locateFail: false
  },

  async onLoad(options) {
    const names = (options.names || '').split(',').filter(Boolean)
    const types = (options.types || '').split(',').filter(Boolean)
    const dayLabel = options.dayLabel || ''
    const city = options.city || ''
    this.setData({ city, dayLabel })
    if (!names.length) {
      this.setData({ loading: false })
      return
    }
    // 1) 拿用户实时位置（gcj-02）
    await this.locate()
    // 2) 批量地理编码
    wx.showLoading({ title: '定位地点中' })
    try {
      const params = { names: names.join(',') }
      if (this.data.city) params.city = this.data.city
      const r = await request({ url: '/api/map/geocode-batch', data: params })
      const results = (r.data && r.data.results) || []
      const locs = names.map((name, i) => {
        const g = results[i]
        const type = types[i] || 'spot'
        const item = {
          name, address: '', lat: null, lng: null, distance: null, ok: false, type,
          image: type === 'meal' ? '' : spotImage(name),
          emoji: MEAL_EMOJI[type === 'meal' ? (name && this._mealType(name)) : 'default'] || '🍽'
        }
        if (g && g.lat != null) {
          item.lat = Number(g.lat)
          item.lng = Number(g.lng)
          item.address = g.address || name
          item.ok = true
          if (this.data.myLat != null) {
            item.distance = haversineKm(this.data.myLat, this.data.myLng, item.lat, item.lng)
          }
        }
        item.distanceText = !item.ok ? '暂无坐标'
          : item.distance == null ? '距离计算中'
          : item.distance < 1 ? `距您 ${(item.distance * 1000).toFixed(0)} m`
          : `距您 ${item.distance.toFixed(1)} km`
        return item
      })
      this.setData({ locs, loading: false })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '地点定位失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  // 餐饮项按名称猜测餐别 emoji（data 里没有 type 时兜底）
  _mealType(name) {
    const n = (name || '').trim()
    if (n.includes('早') || n.includes('包') || n.includes('面')) return 'breakfast'
    if (n.includes('晚') || n.includes('夜') || n.includes('火锅') || n.includes('烧烤')) return 'dinner'
    return 'lunch'
  },


  locate() {
    return new Promise((resolve) => {
      wx.getLocation({
        type: 'gcj02',
        success: (res) => {
          this.setData({ myLat: res.latitude, myLng: res.longitude, locateFail: false })
          resolve()
        },
        fail: () => {
          this.setData({ locateFail: true })
          resolve()
        }
      })
    })
  },

  retryLocate() {
    this.setData({ locateFail: false })
    this.locate()
  },

  onNav(e) {
    const i = e.currentTarget.dataset.i
    const l = this.data.locs[i]
    if (!l.ok) {
      wx.showToast({ title: '该景点暂无坐标', icon: 'none' })
      return
    }
    openMultiMap({ lat: l.lat, lng: l.lng, name: l.name, address: l.address })
  }
})

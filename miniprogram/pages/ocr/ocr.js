const { request } = require('../../utils/request')
const env = require('../../config/env')
const app = getApp()

function readFileBase64(filePath) {
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().readFile({
      filePath,
      encoding: 'base64',
      success: (res) => resolve(res.data),
      fail: reject
    })
  })
}

// 本地示例（USE_MOCK 或视觉 key 未配时由后端返回同样结构的示例；此处用于纯前端预览兜底）
function mockTrip(city, spots) {
  const day = {
    day_number: 1,
    date_label: '第1天',
    spots: (spots || ['西湖', '灵隐寺']).slice(0, 3).map((n) => ({
      name: n, address: city, time_slot: 'morning', duration_min: 120,
      ticket_price: 0, category: '人文历史', description: '示例景点'
    })),
    meals: [{ name: '本地餐厅', type: 'lunch', avg_price: 80, specialty: '特色菜', address: city }],
    transport: [{ from: '酒店', to: spots ? spots[0] : '西湖', mode: '地铁', duration_min: 30, cost: 5 }],
    budget: 400,
    tips: '• 出行前查看天气\n• 热门景点建议错峰'
  }
  return {
    id: 'ocr', title: city + '2日游', city, days: 2, route_type: 'popular',
    crowd_type: '朋友', budget_level: '舒适',
    content: { itinerary: [day], total_budget: 800 }
  }
}

function mockResult(mode, mediaType) {
  if (mode === 'itinerary') {
    return {
      mode: 'itinerary', media_type: mediaType,
      recognized: { city: '杭州', days: 2, spots: ['西湖', '灵隐寺', '河坊街', '西溪湿地'] },
      trip: mockTrip('杭州', ['西湖', '灵隐寺', '河坊街'])
    }
  }
  return {
    mode: 'scene', media_type: mediaType,
    recognized: { place: '西湖', city: '杭州', description: '中国著名淡水湖，三面云山一面城，西湖十景享誉中外。', confidence: 0.93 },
    recommended_spots: [
      { name: '断桥残雪', category: '人文历史', reason: '西湖十景之一，白堤起点，赏湖最佳机位', duration_min: 60, ticket_price: 0 },
      { name: '雷峰塔', category: '人文历史', reason: '登塔俯瞰西湖全景，傍晚夕照尤美', duration_min: 90, ticket_price: 40 },
      { name: '苏堤春晓', category: '自然风光', reason: '贯穿西湖的长堤，晨跑骑行皆宜', duration_min: 80, ticket_price: 0 },
      { name: '三潭印月', category: '网红打卡', reason: '需乘船登岛，一元纸币背面取景地', duration_min: 120, ticket_price: 55 },
      { name: '河坊街', category: '美食', reason: '南宋御街，小吃与老字号云集', duration_min: 100, ticket_price: 0 }
    ],
    trip: mockTrip('杭州', ['断桥残雪', '雷峰塔', '苏堤春晓'])
  }
}

Page({
  data: {
    mode: 'itinerary',
    mediaType: 'image',
    filePath: '',
    result: null,
    recognizing: false
  },

  setMode(e) {
    const m = e.currentTarget.dataset.m
    if (m === this.data.mode) return
    this.setData({ mode: m, filePath: '', result: null })
  },

  choose() {
    const isScene = this.data.mode === 'scene'
    wx.chooseMedia({
      count: 1,
      mediaType: isScene ? ['image', 'video'] : ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const f = res.tempFiles[0]
        const mt = f.fileType === 'video' ? 'video' : 'image'
        this.setData({ filePath: f.tempFilePath, mediaType: mt, result: null })
      }
    })
  },

  async recognize() {
    if (!this.data.filePath || this.data.recognizing) return
    this.setData({ recognizing: true })
    wx.showLoading({ title: 'AI 识别中' })
    try {
      let r
      if (env.USE_MOCK) {
        await new Promise((res) => setTimeout(res, 500))
        r = { data: mockResult(this.data.mode, this.data.mediaType) }
      } else {
        const b64 = await readFileBase64(this.data.filePath)
        const filename = this.data.mediaType === 'video' ? 'video.mp4' : 'image.jpg'
        r = await request({
          url: '/api/ocr/recognize',
          method: 'POST',
          data: { file_base64: b64, filename, mode: this.data.mode }
        })
      }
      this.setData({ result: r.data, recognizing: false })
      wx.hideLoading()
    } catch (e) {
      this.setData({ recognizing: false })
      wx.hideLoading()
    }
  },

  useResult() {
    const t = this.data.result && this.data.result.trip
    if (!t) return
    app.globalData.previewTrip = t
    wx.redirectTo({ url: '/pages/detail/detail?id=preview' })
  }
})

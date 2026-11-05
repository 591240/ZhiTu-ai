const { request } = require('../../utils/request')
const app = getApp()

// 后端 ocr 接口的 base64 上限是 8MB（原始约 6MB），前端先拦一道，
// 免得把整张原图传上去再被 413 打回来。
const MAX_FILE_BYTES = 6 * 1024 * 1024

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

function fileSize(filePath) {
  try {
    return wx.getFileSystemManager().statSync(filePath).size || 0
  } catch (e) {
    return 0
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
    const size = fileSize(this.data.filePath)
    if (size > MAX_FILE_BYTES) {
      wx.showToast({ title: '文件超过 6MB，请压缩后再试', icon: 'none' })
      return
    }
    this.setData({ recognizing: true })
    wx.showLoading({ title: 'AI 识别中' })
    try {
      const b64 = await readFileBase64(this.data.filePath)
      const filename = this.data.mediaType === 'video' ? 'video.mp4' : 'image.jpg'
      const r = await request({
        url: '/api/ocr/recognize',
        method: 'POST',
        data: { file_base64: b64, filename, mode: this.data.mode },
        timeout: 120000
      })
      this.setData({ result: r.data, recognizing: false })
      wx.hideLoading()
    } catch (e) {
      this.setData({ recognizing: false })
      wx.hideLoading()
      wx.showToast({ title: (e && e.message) || '识别失败，请重试', icon: 'none' })
    }
  },

  useResult() {
    const t = this.data.result && this.data.result.trip
    if (!t) return
    app.globalData.previewTrip = t
    wx.redirectTo({ url: '/pages/detail/detail?id=preview' })
  }
})

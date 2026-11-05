// utils/request.js —— 网络请求封装（只走真实后端）
//
// 这里曾经有一整套 mock 分支：USE_MOCK=true 时直接返回本地示例数据。
// 代价是 mock 的响应结构和后端逐渐漂移（收藏列表、created_at 单位、is_vip 命名），
// 关掉 mock 才发现页面是坏的。现在只保留真实请求，要联调就起后端。

const env = require('../config/env')
const storage = require('./storage')

const TIMEOUT = 30000

function handleUnauthorized() {
  storage.remove('token')
  storage.remove('userInfo')
  const app = getApp()
  if (app) {
    app.globalData.token = ''
    app.globalData.userInfo = null
  }
  // 已经在登录页就不要重复跳转
  const pages = getCurrentPages()
  const cur = pages.length ? pages[pages.length - 1].route : ''
  if (cur && cur.indexOf('login') >= 0) return
  wx.reLaunch({ url: '/pages/login/login' })
}

function request(options) {
  return new Promise((resolve, reject) => {
    const token = storage.getToken()
    wx.request({
      url: env.BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      timeout: options.timeout || TIMEOUT,
      header: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      success(res) {
        if (res.statusCode === 401) {
          handleUnauthorized()
          reject({ code: 401, message: '登录已失效，请重新登录' })
          return
        }
        if (res.statusCode >= 500) {
          wx.showToast({ title: '服务异常，请稍后重试', icon: 'none' })
          reject({ code: res.statusCode, message: '服务异常' })
          return
        }
        if (res.data && res.data.code === 0) {
          resolve(res.data)
        } else {
          const payload = res.data || { code: -1, message: '请求失败' }
          wx.showToast({ title: payload.message || '请求失败', icon: 'none' })
          reject(payload)
        }
      },
      fail(err) {
        wx.showToast({ title: '网络异常，请重试', icon: 'none' })
        reject({ code: -1, message: '网络异常', raw: err })
      }
    })
  })
}

// 流式请求（用于对话问答）。解析 SSE：每段形如 "data: {json}\n\n"。
// onDone(err) 保证只调用一次——之前没有 fail 回调，断网后 sending 永远为 true，
// 输入框直接卡死，只能退出重进页面。
function streamRequest(url, data, onChunk, onDone) {
  let buf = ''
  let finished = false
  const finish = (err) => {
    if (finished) return
    finished = true
    onDone && onDone(err)
  }

  const handleText = (text) => {
    buf += text
    let idx
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const raw = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      for (const ln of raw.split('\n')) {
        if (!ln.startsWith('data:')) continue
        const payload = ln.slice(5).trim()
        if (payload === '[DONE]') { finish(); return }
        try {
          const obj = JSON.parse(payload)
          if (obj.done) { finish(); return }
          if (obj.error) { finish({ code: -1, message: obj.error }); return }
          if (obj.text) onChunk(obj.text)
        } catch (e) { /* 忽略不完整片段 */ }
      }
    }
  }

  const token = storage.getToken()
  const task = wx.request({
    url: env.BASE_URL + url,
    method: 'POST',
    data,
    timeout: 120000,
    header: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Accept': 'text/event-stream'
    },
    enableChunked: true,
    responseType: 'text',
    success(res) {
      if (res.statusCode === 401) {
        handleUnauthorized()
        finish({ code: 401, message: '登录已失效' })
        return
      }
      // 非流式错误（积分不足 4001 / 配额用尽 4002）会整段返回 JSON
      if (res.data && typeof res.data === 'string') {
        try {
          const obj = JSON.parse(res.data)
          if (obj.code && obj.code !== 0) {
            finish({ code: obj.code, message: obj.message || '请求失败' })
            return
          }
        } catch (e) { /* 不是 JSON，说明是正常 SSE 流 */ }
      }
      finish()
    },
    fail(err) {
      finish({ code: -1, message: '网络异常', raw: err })
    }
  })

  task.onChunkReceived((res) => {
    try {
      const text = new TextDecoder('utf-8').decode(res.data)
      handleText(text)
    } catch (e) {
      finish({ code: -1, message: '解析响应失败' })
    }
  })

  return {
    abort() {
      try { task.abort() } catch (e) {}
      finish({ code: -2, message: '已取消' })
    }
  }
}

module.exports = { request, streamRequest }

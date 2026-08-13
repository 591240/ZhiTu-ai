// utils/request.js —— 网络请求封装（mock 优先，可切真实后端）

const env = require('../config/env')
const mock = require('./mock')
const storage = require('./storage')

function request(options) {
  return new Promise((resolve, reject) => {
    // ===== Mock 模式：直接走本地示例数据 =====
    if (env.USE_MOCK) {
      try {
        const res = mock.handleMock(options.url, options.method || 'GET', options.data)
        // 模拟网络延迟，体验更真实
        setTimeout(() => resolve(res), 280)
      } catch (e) {
        reject(e)
      }
      return
    }

    // ===== 真实后端模式 =====
    const token = storage.getToken()
    wx.request({
      url: env.BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      success(res) {
        if (res.statusCode === 401) {
          storage.remove('token')
          wx.redirectTo({ url: '/pages/login/login' })
          reject(new Error('未登录'))
          return
        }
        if (res.data && res.data.code === 0) {
          resolve(res.data)
        } else {
          wx.showToast({ title: (res.data && res.data.message) || '请求失败', icon: 'none' })
          reject(res.data)
        }
      },
      fail(err) {
        wx.showToast({ title: '网络异常，请重试', icon: 'none' })
        reject(err)
      }
    })
  })
}

// 流式请求（用于对话问答）。解析 SSE：每段形如 "data: {json}\n\n"。
let _sseDone = false
function streamRequest(url, data, onChunk, onDone) {
  let buf = ''
  let finished = false
  const finish = () => { if (!finished) { finished = true; onDone && onDone() } }

  const handleText = (text) => {
    buf += text
    let idx
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const raw = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      for (const ln of raw.split('\n')) {
        if (ln.startsWith('data:')) {
          const payload = ln.slice(5).trim()
          if (payload === '[DONE]') { finish(); return }
          try {
            const obj = JSON.parse(payload)
            if (obj.done) { finish(); return }
            if (obj.text) onChunk(obj.text)
            if (obj.error) { finish(); return }
          } catch (e) { /* 忽略不完整片段 */ }
        }
      }
    }
  }

  if (env.USE_MOCK) {
    const answer = mock.fakeQA(data.question || '')
    const chunks = answer.match(/[^。！？]*[。！？]?/g).filter(Boolean)
    let i = 0
    const timer = setInterval(() => {
      if (i < chunks.length) {
        handleText('data: ' + JSON.stringify({ text: chunks[i] }) + '\n\n')
        i++
      } else {
        clearInterval(timer)
        handleText('data: ' + JSON.stringify({ done: true }) + '\n\n')
      }
    }, 120)
    return { abort: () => { clearInterval(timer); finish() } }
  }

  const token = storage.getToken()
  const task = wx.request({
    url: env.BASE_URL + url,
    method: 'POST',
    data,
    header: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Accept': 'text/event-stream'
    },
    enableChunked: true,
    responseType: 'text',
    success(res) {
      // 非流式错误（如积分不足 4001）会在 success 里返回 JSON
      if (res.data && typeof res.data === 'string') {
        try {
          const obj = JSON.parse(res.data)
          if (obj.code && obj.code !== 0) {
            const err = new Error(obj.message || '请求失败')
            err.code = obj.code
            if (!finished) { finished = true; onDone && onDone(err) }
            return
          }
        } catch (e) { /* 不是 JSON，继续走流式 */ }
      }
      finish()
    }
  })
  task.onChunkReceived((res) => {
    const text = new TextDecoder('utf-8').decode(res.data)
    handleText(text)
  })
  return task
}

module.exports = { request, streamRequest }

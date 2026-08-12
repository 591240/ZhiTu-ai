// utils/track.js —— 数据埋点上报封装（本地队列 + 批量上报）

const { request } = require('./request')
const storage = require('./storage')

let queue = []
let timer = null
let flushing = false
const FLUSH_INTERVAL = 4000   // 4s 内自动 flush
const MAX_BATCH = 20          // 攒够 20 条立即上报

function track(type, props) {
  if (!type) return
  queue.push({ type, props: props || {} })
  if (queue.length >= MAX_BATCH) {
    flush()
  } else {
    schedule()
  }
}

function schedule() {
  if (timer) return
  timer = setTimeout(() => { timer = null; flush() }, FLUSH_INTERVAL)
}

async function flush() {
  if (flushing || queue.length === 0) return
  if (!storage.getToken()) { queue = []; return }  // 未登录不上报
  flushing = true
  const batch = queue.splice(0, MAX_BATCH)
  try {
    await request({ url: '/api/track', method: 'POST', data: { events: batch } })
  } catch (e) {
    // 上报失败不阻塞主流程，丢弃本批
  } finally {
    flushing = false
  }
}

module.exports = { track, flush }

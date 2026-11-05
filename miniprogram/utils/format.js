// utils/format.js —— 格式化工具

// 金额格式化（分 -> 元，或数字 -> ¥x.xx）
function money(n) {
  const num = typeof n === 'string' ? parseFloat(n) : n
  if (isNaN(num)) return '0'
  return num % 1 === 0 ? String(num) : num.toFixed(2)
}

// 相对时间（时间戳 -> x天前）
// 后端统一返回毫秒；这里仍做一次兜底：小于 1e12 的按秒处理，
// 免得哪天某个接口又漏了 *1000，整页时间集体变成 1970 年。
function fromNow(ts) {
  let n = Number(ts) || 0
  if (n > 0 && n < 1e12) n *= 1000
  const diff = Date.now() - n
  const day = 86400000
  if (diff < 0) return '刚刚'
  if (diff < day) return '今天'
  if (diff < 2 * day) return '昨天'
  if (diff < 7 * day) return Math.floor(diff / day) + '天前'
  const d = new Date(n)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

// 日期标签
function dateLabel(day) {
  const arr = ['一', '二', '三', '四', '五', '六', '七', '八']
  return `第${arr[day - 1] || day}天`
}

// 时段中文
function slotText(slot) {
  return ({ morning: '上午', afternoon: '下午', evening: '晚上' })[slot] || slot
}

// 路线风格标签
function routeTag(type) {
  return type === 'niche' ? { text: '小众', cls: 'tag-niche' } : { text: '大众', cls: 'tag-popular' }
}

module.exports = { money, fromNow, dateLabel, slotText, routeTag }

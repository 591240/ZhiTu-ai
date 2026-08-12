// utils/media.js —— 景点封面图与第三方平台跳转
// 封面图：按景点名取真实照片（loremflickr，免 key，稳定 hash 防抖）。
// 平台跳转：抖音/小红书/视频号 搜索该景点攻略（微信内无法直接拉起，复制链接+引导打开）。

// 简单字符串 hash，用于锁定同一景点每次取到同一张图
function hashStr(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h)
}

// 景点封面图：带稳定性后缀，开发者工具需勾"不校验合法域名"
function spotImage(name) {
  const n = (name || '景点').trim()
  const lock = hashStr(n) % 1000
  return `https://loremflickr.com/600/400/${encodeURIComponent(n)}?lock=${lock}`
}

// 城市封面图：优先使用精选的真实风景照；未配置城市再回退到 loremflickr
// 说明：以下 URL 来自公开图库，本地开发需勾选「不校验合法域名」；
// 正式上线前建议下载到 images/cities/ 本地目录，避免外部域名白名单问题。
const CITY_IMAGES = {
  '杭州': 'https://images.unsplash.com/photo-1547981609-4b6bfe67ca0b?auto=format&fit=crop&w=640&q=80',
  '成都': 'https://images.unsplash.com/photo-1590736969955-71cc94901144?auto=format&fit=crop&w=640&q=80',
  '西安': 'https://images.unsplash.com/photo-1508804185872-d7badad00f7d?auto=format&fit=crop&w=640&q=80',
  '苏州': 'https://images.unsplash.com/photo-1584596859861-39d7a5243952?auto=format&fit=crop&w=640&q=80',
  '重庆': 'https://images.unsplash.com/photo-1542059604-ef4a225f6b54?auto=format&fit=crop&w=640&q=80',
  '厦门': 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=640&q=80',
  '长沙': 'https://images.unsplash.com/photo-1598887142487-3c854d51eabb?auto=format&fit=crop&w=640&q=80',
  '南京': 'https://images.unsplash.com/photo-1569423304452-85b61b63c224?auto=format&fit=crop&w=640&q=80'
}
function cityImage(city) {
  const n = (city || '旅行').trim()
  if (CITY_IMAGES[n]) return CITY_IMAGES[n]
  const lock = hashStr(n) % 1000
  return `https://loremflickr.com/640/360/${encodeURIComponent(n)}?lock=${lock}`
}

// 城市 → emoji（稳定封面图标，列表/无网兜底）
const CITY_EMOJI = {
  '杭州': '🌊', '北京': '🏯', '上海': '🌆', '成都': '🐼', '西安': '🏛️', '重庆': '🌃',
  '广州': '🌴', '深圳': '🏙️', '香港': '🏝️', '澳门': '🎰', '三亚': '🏖️', '云南': '⛰️',
  '厦门': '🌊', '南京': '🏯', '武汉': '🌉', '长沙': '🍜', '苏州': '🌸', '丽江': '🏔️',
  '青岛': '🌊', '天津': '🌉', '大理': '⛰️', '拉萨': '🏔️', '台北': '🌆', '桂林': '🏞️'
}
function cityEmoji(city) {
  return CITY_EMOJI[(city || '').trim()] || '📍'
}

// 各平台"搜索该景点"的链接
function platformSearchUrl(platform, name) {
  const q = encodeURIComponent(name)
  if (platform === 'douyin') {
    // 抖音网页搜索（复制后在 App/浏览器打开）
    return `https://www.douyin.com/search/${q}`
  }
  if (platform === 'xiaohongshu') {
    return `https://www.xiaohongshu.com/search_result?keyword=${q}`
  }
  if (platform === 'channels') {
    // 微信视频号：公众号/视频号搜索页（同生态内最顺畅）
    return `https://weixin.qq.com/?search=${q}`
  }
  return ''
}

function openPlatform(name) {
  const n = (name || '该景点').trim()
  wx.showActionSheet({
    itemList: ['抖音', '小红书', '微信视频号'],
    success: (res) => {
      const map = ['douyin', 'xiaohongshu', 'channels']
      const platform = map[res.tapIndex]
      const url = platformSearchUrl(platform, n)
      if (!url) return
      const label = platform === 'douyin' ? '抖音' : platform === 'xiaohongshu' ? '小红书' : '微信视频号'
      wx.setClipboardData({
        data: url,
        success: () => {
          wx.showModal({
            title: `已复制${label}搜索链接`,
            content: `请在${label}App 内粘贴打开，查看「${n}」的图文/视频攻略。`,
            showCancel: false,
            confirmText: '知道了'
          })
        }
      })
    }
  })
}

// ===== 门票购买渠道对比 + 公众号预约 =====

// 生成某景点的购票渠道列表（景区官方优先、附带 OTA 比价）
function ticketChannels(spot) {
  const name = (spot && spot.name) || '该景点'
  const official = (spot && spot.official_account) || ''
  const channels = []
  if (official) {
    channels.push({
      key: 'official',
      name: '景区官方公众号/小程序',
      note: '通常最便宜 · 可直接预约',
      recommend: true,
      kind: 'account',
      value: official
    })
  }
  const ota = [
    { key: 'ctrip', name: '携程', note: '比价常用 · 退改灵活', search: `https://www.ctrip.com/search?q=${encodeURIComponent(name + ' 门票')}` },
    { key: 'meituan', name: '美团', note: '常有限时折扣', search: `https://www.meituan.com/search?q=${encodeURIComponent(name + ' 门票')}` },
    { key: 'fliggy', name: '飞猪', note: '阿里会员价', search: `https://www.fliggy.com/search?q=${encodeURIComponent(name + ' 门票')}` },
    { key: 'tongcheng', name: '同程旅行', note: '周边游常用', search: `https://www.ly.com/search?q=${encodeURIComponent(name + ' 门票')}` },
    { key: 'douyin', name: '抖音团购', note: '节假日常更便宜', search: `https://www.douyin.com/search/${encodeURIComponent(name + ' 团购')}` }
  ]
  ota.forEach((c) => channels.push(Object.assign({ recommend: false, kind: 'search' }, c)))
  return channels
}

// 点击某个购票渠道：官方复制公众号名并引导微信搜索；OTA 复制搜索链接并引导打开
function chooseTicketChannel(ch) {
  if (!ch) return
  if (ch.kind === 'account') {
    wx.setClipboardData({
      data: ch.value,
      success: () => {
        wx.showModal({
          title: '已复制官方渠道名称',
          content: `请打开微信 → 搜索「${ch.value}」公众号/小程序，购票并预约（通常最便宜）。`,
          showCancel: false,
          confirmText: '去微信'
        })
      }
    })
    return
  }
  // OTA 比价
  wx.setClipboardData({
    data: ch.search,
    success: () => {
      wx.showModal({
        title: `已复制${ch.name}搜索链接`,
        content: `请在${ch.name}App 或浏览器粘贴打开，对比「${ch.name}」上的票价后再下单。`,
        showCancel: false,
        confirmText: '知道了'
      })
    }
  })
}

// 需预约景点：复制官方公众号名 + 引导在微信搜索预约
function openBooking(spot) {
  const name = (spot && spot.name) || '该景点'
  const account = (spot && spot.official_account) || name
  const tip = (spot && spot.official_account)
    ? `请打开微信 → 搜索「${account}」公众号，进入菜单预约/购票（该景点需提前预约）。`
    : `请打开微信 → 搜索「${name}」官方公众号，进入菜单预约（该景点需提前预约）。`
  wx.setClipboardData({
    data: account,
    success: () => {
      wx.showModal({
        title: '已复制预约渠道',
        content: tip,
        showCancel: false,
        confirmText: '去微信'
      })
    }
  })
}

// 餐饮「团购/查低价」渠道（逻辑同门票，但搜索词换成餐饮团购/探店）
function dealChannels(meal) {
  const name = (meal && meal.name) || '该餐厅'
  const channels = [
    { key: 'meituan', name: '美团', note: '到店套餐/代金券常用', search: `https://www.meituan.com/search?q=${encodeURIComponent(name + ' 团购')}` },
    { key: 'dianping', name: '大众点评', note: '看真实评价+买单优惠', search: `https://www.dianping.com/search?q=${encodeURIComponent(name)}` },
    { key: 'douyin', name: '抖音团购', note: '短视频套餐常更便宜', search: `https://www.douyin.com/search/${encodeURIComponent(name + ' 团购')}` },
    { key: 'xiaohongshu', name: '小红书', note: '探店笔记/隐藏优惠', search: `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(name + ' 团购')}` }
  ]
  channels.forEach((c) => Object.assign(c, { recommend: false, kind: 'search' }))
  return channels
}

// 根据 AI 推荐的渠道名，从渠道表里模糊匹配出对应渠道对象
function matchChannel(channels, channelName) {
  if (!channelName) return null
  const n = (channelName || '').trim()
  return channels.find((c) => c.name.indexOf(n) >= 0 || n.indexOf(c.name) >= 0) || null
}

// 门票：若 AI 已给出推荐渠道，直接打开该渠道；否则返回 false 由调用方弹比价列表
function openTicketChannel(spot) {
  const ch = matchChannel(ticketChannels(spot), spot && spot.ticket_channel)
  if (ch) { chooseTicketChannel(ch); return true }
  return false
}

// 餐饮团购：同上
function openDealChannel(meal) {
  const ch = matchChannel(dealChannels(meal), meal && meal.deal_channel)
  if (ch) { chooseTicketChannel(ch); return true }
  return false
}

module.exports = {
  spotImage,
  cityImage,
  cityEmoji,
  openPlatform,
  platformSearchUrl,
  ticketChannels,
  chooseTicketChannel,
  openBooking,
  dealChannels,
  openTicketChannel,
  openDealChannel
}

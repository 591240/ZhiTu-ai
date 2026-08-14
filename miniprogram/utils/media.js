// utils/media.js —— 景点封面图与第三方平台跳转
// 封面图：按景点名取真实照片（loremflickr，免 key，稳定 hash 防抖）。
// 平台跳转：抖音/小红书 复制搜索词，用户打开对应 App 后粘贴搜索

// 简单字符串 hash，用于锁定同一景点每次取到同一张图
function hashStr(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h)
}

// 景点封面图兜底：当后端未返回图片或图片加载失败时使用。
// 用 loremflickr 按景点名关键词搜索，保证任何城市/景点都有图显示。
function spotImage(name, city) {
  const n = (name || '景点').trim()
  const c = (city || '').trim()
  const q = c ? `${encodeURIComponent(c)},${encodeURIComponent(n)}` : encodeURIComponent(n)
  const lock = hashStr(n + c) % 1000
  return `https://loremflickr.com/640/360/${q}/all?lock=${lock}`
}

// 城市封面图：优先使用本地真实照片 /images/cities/城市名.jpg；
// 没有本地图时，走 loremflickr 关键词图（保证城市内容相关，不会西安配长城）。
// 上线前建议把真实摄影图放到 miniprogram/images/cities/ 目录，避免外部域名白名单问题。
const CITY_ONLINE = {
  '杭州': 'https://loremflickr.com/640/360/hangzhou,westlake?lock=201',
  '成都': 'https://loremflickr.com/640/360/chengdu,panda?lock=202',
  '西安': 'https://loremflickr.com/640/360/xian,terracotta?lock=203',
  '苏州': 'https://loremflickr.com/640/360/suzhou,garden?lock=204',
  '重庆': 'https://loremflickr.com/640/360/chongqing,hongyadong?lock=205',
  '厦门': 'https://loremflickr.com/640/360/xiamen,gulangyu?lock=206',
  '长沙': 'https://loremflickr.com/640/360/changsha,orangeisle?lock=207',
  '南京': 'https://loremflickr.com/640/360/nanjing,confucius?lock=208'
}
function cityImage(city) {
  const n = (city || '旅行').trim()
  return `/images/cities/${n}.jpg`
}
function cityImageOnline(city) {
  const n = (city || '旅行').trim()
  if (CITY_ONLINE[n]) return CITY_ONLINE[n]
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

// 各平台"搜索该景点"的关键词（更自然，用户复制后到 App 内粘贴搜索）
function platformSearchKeyword(platform, name) {
  const n = (name || '该景点').trim()
  if (platform === 'douyin') return `${n}攻略`
  if (platform === 'xiaohongshu') return `${n}攻略`
  return ''
}

// 兼容旧导出：仍返回网页搜索链接，但 openPlatform 内部不再使用
function platformSearchUrl(platform, name) {
  const q = encodeURIComponent(name || '')
  if (platform === 'douyin') return `https://www.douyin.com/search/${q}`
  if (platform === 'xiaohongshu') return `https://www.xiaohongshu.com/search_result?keyword=${q}`
  if (platform === 'channels') return `https://weixin.qq.com/?search=${q}`
  return ''
}

function openPlatform(name) {
  const n = (name || '该景点').trim()
  wx.showActionSheet({
    itemList: ['抖音', '小红书'],
    success: (res) => {
      const map = ['douyin', 'xiaohongshu']
      const platform = map[res.tapIndex]
      const label = platform === 'douyin' ? '抖音' : '小红书'

      // 抖音/小红书：复制搜索词
      const keyword = platformSearchKeyword(platform, n)
      wx.setClipboardData({
        data: keyword,
        success: () => {
          wx.showModal({
            title: `已复制${label}搜索词`,
            content: `请打开${label} → 粘贴搜索「${keyword}」，查看「${n}」的图文/视频攻略。`,
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
    { key: 'ctrip', name: '携程', note: '比价常用 · 退改灵活', search: `https://www.ctrip.com/search?q=${encodeURIComponent(name + ' 门票')}`, appId: 'wx0e6ed4f51db9d078', keyword: name + ' 门票' },
    { key: 'meituan', name: '美团', note: '常有限时折扣', search: `https://www.meituan.com/search?q=${encodeURIComponent(name + ' 门票')}`, appId: 'wxde8ac0a21135c07d', keyword: name + ' 门票' },
    { key: 'dianping', name: '大众点评', note: '看评价 · 买票团购', search: `https://www.dianping.com/search?q=${encodeURIComponent(name + ' 门票')}`, appId: 'wx734c1ad7b3562129', keyword: name + ' 门票' },
    { key: 'fliggy', name: '飞猪', note: '阿里会员价', search: `https://www.fliggy.com/search?q=${encodeURIComponent(name + ' 门票')}`, keyword: name + ' 门票' },
    { key: 'tongcheng', name: '同程旅行', note: '周边游常用', search: `https://www.ly.com/search?q=${encodeURIComponent(name + ' 门票')}`, keyword: name + ' 门票' },
    { key: 'douyin', name: '抖音团购', note: '节假日常更便宜', search: `https://www.douyin.com/search/${encodeURIComponent(name + ' 团购')}`, keyword: name + ' 门票' }
  ]
  ota.forEach((c) => channels.push(Object.assign({ recommend: false, kind: 'search' }, c)))
  return channels
}

// 点击某个购票渠道：官方复制公众号名并引导微信搜索；OTA 支持小程序的直接跳转，否则复制搜索链接
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
  // OTA 比价：能跳转小程序的直接跳
  if (ch.appId) {
    openMiniProgramSearch(ch.appId, ch.name, ch.keyword || '')
    return
  }
  // 不支持小程序的 OTA（飞猪/同程/抖音/小红书）复制搜索词，用户到 App 内粘贴搜索
  const kw = ch.keyword || (ch.search || '')
  wx.setClipboardData({
    data: kw,
    success: () => {
      wx.showModal({
        title: `已复制${ch.name}搜索词`,
        content: `请打开${ch.name} → 粘贴搜索「${kw}」，对比票价后再下单。`,
        showCancel: false,
        confirmText: '知道了'
      })
    }
  })
}

// 跳转到第三方小程序并尝试带搜索关键词（extraData 由目标小程序自行解析）
function openMiniProgramSearch(appId, platformName, keyword) {
  wx.navigateToMiniProgram({
    appId: appId,
    extraData: { keyword: keyword || '' },
    success: () => {
      wx.showToast({ title: `已打开${platformName}，请搜索预约`, icon: 'none' })
    },
    fail: () => {
      wx.showModal({
        title: '跳转失败',
        content: `无法直接打开${platformName}，请确认已在「设置-小程序」中授权，或在App内搜索该景点。`,
        showCancel: false,
        confirmText: '知道了'
      })
    }
  })
}

// 预约/购票：优先打开公众号资料页；没有原始 ID 则跳第三方小程序搜景点
function openBooking(spot) {
  const name = (spot && spot.name) || '该景点'
  const raw = (spot && spot.official_account) || ''
  const parts = raw.split('|').map((s) => s.trim()).filter(Boolean)
  const gh = parts.find((s) => s.startsWith('gh_')) || (raw.trim().startsWith('gh_') ? raw.trim() : '')
  const accountName = parts.find((s) => !s.startsWith('gh_')) || (raw.trim() && !raw.trim().startsWith('gh_') ? raw.trim() : '')

  // 有公众号原始 ID，直接打开公众号资料页
  if (gh && wx.openOfficialAccountProfile) {
    wx.openOfficialAccountProfile({
      username: gh,
      success: () => {},
      fail: () => openBookingFallback(name, accountName)
    })
    return
  }

  openBookingFallback(name, accountName)
}

function openBookingFallback(spotName, accountName) {
  const channels = [
    { name: '美团', appId: 'wxde8ac0a21135c07d' },
    { name: '大众点评', appId: 'wx734c1ad7b3562129' },
    { name: '携程', appId: 'wx0e6ed4f51db9d078' }
  ]
  wx.showActionSheet({
    itemList: channels.map((c) => `打开${c.name}搜「${spotName}」`),
    success: (res) => {
      const ch = channels[res.tapIndex]
      wx.navigateToMiniProgram({
        appId: ch.appId,
        extraData: { keyword: spotName },
        success: () => {
          wx.showToast({ title: `已打开${ch.name}，请搜索预约`, icon: 'none' })
        },
        fail: () => {
          // 跳转失败 fallback：复制公众号名称
          const copy = accountName || spotName
          wx.setClipboardData({
            data: copy,
            success: () => {
              wx.showModal({
                title: '已复制预约渠道',
                content: `请打开微信 → 搜索「${copy}」公众号，进入菜单预约/购票。`,
                showCancel: false,
                confirmText: '知道了'
              })
            }
          })
        }
      })
    }
  })
}

// 餐饮「团购/查低价」渠道（逻辑同门票，但搜索词换成餐饮团购/探店）
function dealChannels(meal) {
  const name = (meal && meal.name) || '该餐厅'
  const channels = [
    { key: 'meituan', name: '美团', note: '到店套餐/代金券常用', search: `https://www.meituan.com/search?q=${encodeURIComponent(name + ' 团购')}`, appId: 'wxde8ac0a21135c07d', keyword: name + ' 团购' },
    { key: 'dianping', name: '大众点评', note: '看真实评价+买单优惠', search: `https://www.dianping.com/search?q=${encodeURIComponent(name)}`, appId: 'wx734c1ad7b3562129', keyword: name },
    { key: 'douyin', name: '抖音团购', note: '短视频套餐常更便宜', search: `https://www.douyin.com/search/${encodeURIComponent(name + ' 团购')}`, keyword: name + ' 团购' },
    { key: 'xiaohongshu', name: '小红书', note: '探店笔记/隐藏优惠', search: `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(name + ' 团购')}`, keyword: name + ' 团购' }
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
  cityImageOnline,
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

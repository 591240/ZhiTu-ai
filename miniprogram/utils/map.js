// utils/map.js —— 地图跳转与购票跳转工具
// "在地图看站点"：先 geocode 拿坐标，再用 wx.openLocation 拉起地图（含导航），零白名单依赖。
// "去12306购买"：复制 12306 H5 深链 + 引导弹窗（小程序内不支持直接购票）。

const { request } = require('./request')

// 打开地图查看指定地点（站点级精准定位 + 导航）
async function openLocation(name) {
  if (!name) return
  wx.showLoading({ title: '定位中' })
  try {
    const r = await request({ url: '/api/map/geocode', data: { name } })
    wx.hideLoading()
    const loc = r.data
    if (!loc || loc.lat == null) {
      wx.showToast({ title: '暂无该地点坐标', icon: 'none' })
      return
    }
    wx.openLocation({
      latitude: Number(loc.lat),
      longitude: Number(loc.lng),
      name: loc.name || name,
      address: loc.address || name,
      scale: 16
    })
  } catch (e) {
    wx.hideLoading()
    wx.showToast({ title: '定位失败', icon: 'none' })
  }
}

// 去 12306 购买：构造 H5 深链并复制到剪贴板 + 引导
function buyOn12306({ from, to, date }) {
  const url = 'https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc'
    + '&fs=' + encodeURIComponent(from)
    + '&ts=' + encodeURIComponent(to)
    + '&date=' + encodeURIComponent(date)
  wx.setClipboardData({
    data: url,
    success: () => {
      wx.showModal({
        title: '已复制购票链接',
        content: '请在浏览器或 12306 App 打开完成购买（小程序内暂不支持直接购票）。',
        showCancel: false,
        confirmText: '知道了'
      })
    }
  })
}

// 地图导航：统一用腾讯地图（wx.openLocation，坐标系 gcj-02 一致，直接拉起 App 导航，最稳）
function openMultiMap(loc) {
  if (!loc || loc.lat == null || loc.lng == null) {
    wx.showToast({ title: '暂无该地点坐标', icon: 'none' })
    return
  }
  wx.openLocation({
    latitude: Number(loc.lat),
    longitude: Number(loc.lng),
    name: loc.name || loc.address || '目的地',
    address: loc.address || loc.name || '',
    scale: 16
  })
}

// haversine 距离（km），输入 gcj-02 经纬度即可（导航距离近似）
function haversineKm(lat1, lng1, lat2, lng2) {
  const R = 6371
  const toRad = (d) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

module.exports = { openLocation, buyOn12306, openMultiMap, haversineKm }

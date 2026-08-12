// utils/storage.js —— 本地存储封装

const KEYS = {
  TOKEN: 'token',
  USER: 'userInfo',
  VIP: 'isVip',
  CITY: 'city',
  TRIPS: 'localTrips',
  BIND_INVITE: 'bindInviteCode'   // 通过分享链接带入的邀请码（登录后自动绑定）
}

function get(key, def) {
  const v = wx.getStorageSync(key)
  return (v === '' || v === undefined || v === null) ? def : v
}

function set(key, val) {
  wx.setStorageSync(key, val)
}

function remove(key) {
  wx.removeStorageSync(key)
}

module.exports = {
  KEYS,
  get,
  set,
  remove,
  getToken: () => get(KEYS.TOKEN, ''),
  setToken: (t) => set(KEYS.TOKEN, t),
  getUser: () => get(KEYS.USER, null),
  setUser: (u) => set(KEYS.USER, u),
  getIsVip: () => get(KEYS.VIP, false),
  setIsVip: (v) => set(KEYS.VIP, v),
  getCity: () => get(KEYS.CITY, '杭州'),
  setCity: (c) => set(KEYS.CITY, c),
  getBindInvite: () => get(KEYS.BIND_INVITE, ''),
  setBindInvite: (c) => set(KEYS.BIND_INVITE, c || '')
}

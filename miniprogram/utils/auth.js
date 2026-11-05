// utils/auth.js —— 认证工具
const storage = require('./storage')
const { request } = require('./request')

// 后端字段是 is_vip（snake_case），前端历史代码读的是 isVip，
// 结果 globalData.isVip 恒为 undefined。统一在这里转一次，别在页面里各写各的。
function normalizeUser(u) {
  if (!u) return null
  return Object.assign({}, u, { isVip: !!(u.isVip || u.is_vip) })
}

function applyLogin(payload) {
  const user = normalizeUser(payload.user)
  storage.setToken(payload.token)
  storage.setUser(user)
  storage.setIsVip(user ? user.isVip : false)
  const app = getApp()
  if (app) {
    app.globalData.token = payload.token
    app.globalData.userInfo = user
    app.globalData.isVip = user ? user.isVip : false
  }
  return Object.assign({}, payload, { user })
}

// 微信登录：wx.login -> 后端换 token -> 存储
// phoneCode 可选：微信手机号快速验证回调返回的 code，传入则一并绑定手机号
function login(phoneCode) {
  return new Promise((resolve, reject) => {
    wx.login({
      success: async (res) => {
        if (!res.code) { reject(new Error('获取登录凭证失败')); return }
        try {
          const r = await request({
            url: '/api/auth/login',
            method: 'POST',
            data: { code: res.code, phone_code: phoneCode || '' }
          })
          resolve(applyLogin(r.data))
        } catch (e) {
          // 透传后端返回的结构化错误，方便上层展示具体原因
          reject(new Error((e && e.message) || '登录失败'))
        }
      },
      fail: () => reject(new Error('wx.login 调用失败'))
    })
  })
}

// 已登录用户绑定/更换手机号
async function bindPhone(phoneCode) {
  const r = await request({ url: '/api/auth/bind-phone', method: 'POST', data: { phone_code: phoneCode } })
  const phone = r.data && r.data.phone
  const user = storage.getUser() || {}
  user.phone = phone || ''
  storage.setUser(user)
  const app = getApp()
  if (app) app.globalData.userInfo = user
  return phone
}

// 手机号 + 短信验证码 登录 / 注册
async function phoneLogin(phone, code) {
  const r = await request({ url: '/api/auth/phone-login', method: 'POST', data: { phone, code } })
  return applyLogin(r.data)
}

// 是否已登录
function isLogin() {
  return !!storage.getToken()
}

module.exports = { login, isLogin, bindPhone, phoneLogin, normalizeUser }

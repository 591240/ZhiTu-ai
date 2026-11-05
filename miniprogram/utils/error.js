// utils/error.js —— 统一的接口错误处理
// form / quick / chat 三处都在重复「积分不足弹窗 + 配额用尽提示」，
// 抽出来避免改一处漏两处。

const env = require('../config/env')

function goMember() {
  wx.navigateTo({ url: '/pages/member/member' })
}

/**
 * 处理规划/问答类接口的错误。
 * @param {object} e request 的 reject 值 {code, message}
 * @returns {boolean} 是否已被处理（true 表示调用方不用再弹提示）
 */
function handleBizError(e) {
  const code = e && e.code
  const msg = (e && e.message) || '请求失败，请重试'

  if (code === 4001) {
    wx.showModal({
      title: '积分不足',
      content: msg,
      confirmText: env.MONETIZATION_ENABLED ? '去充值' : '知道了',
      showCancel: env.MONETIZATION_ENABLED,
      cancelText: '取消',
      success: (res) => { if (res.confirm && env.MONETIZATION_ENABLED) goMember() }
    })
    return true
  }

  if (code === 4002) {
    wx.showModal({
      title: '今日次数已用完',
      content: msg,
      confirmText: '知道了',
      showCancel: false
    })
    return true
  }

  return false
}

module.exports = { handleBizError, goMember }

const app = getApp()
const { request } = require('../../utils/request')

Page({
  data: {
    version: '1.0.0'
  },

  goMember() { wx.navigateTo({ url: '/pages/member/member' }) },
  goCollection() { wx.navigateTo({ url: '/pages/collection/collection' }) },
  goPublished() { wx.navigateTo({ url: '/pages/published/published' }) },
  goChat() { wx.navigateTo({ url: '/pages/chat/chat' }) },

  goAgreement(e) {
    const type = e.currentTarget.dataset.type || 'privacy'
    wx.navigateTo({ url: '/pages/agreement/agreement?tab=' + type })
  },

  goFeedback() {
    wx.navigateTo({ url: '/pages/feedback/feedback' })
  },

  onClear() {
    wx.showModal({
      title: '清空本地数据',
      content: '将删除本机保存的行程与收藏，确定？',
      success: (r) => {
        if (r.confirm) {
          wx.clearStorageSync()
          wx.showToast({ title: '已清空', icon: 'success' })
        }
      }
    })
  },

  onDeactivate() {
    wx.showModal({
      title: '注销账号',
      content: '注销后账号将无法登录，行程等数据将被清除，确定继续？',
      confirmText: '确认注销',
      confirmColor: '#FF4D4F',
      success: async (r) => {
        if (!r.confirm) return
        wx.showLoading({ title: '处理中' })
        try {
          const res = await request({ url: '/api/user/deactivate', method: 'POST' })
          wx.hideLoading()
          if (res.code === 0) {
            wx.removeStorageSync('token')
            wx.removeStorageSync('userInfo')
            app.globalData.userInfo = null
            wx.showToast({ title: '已注销', icon: 'success' })
            setTimeout(() => wx.reLaunch({ url: '/pages/login/login' }), 800)
          } else {
            wx.showToast({ title: res.message || '注销失败', icon: 'none' })
          }
        } catch (e) {
          wx.hideLoading()
          wx.showToast({ title: '注销失败', icon: 'none' })
        }
      }
    })
  },

  logout() {
    wx.showModal({
      title: '退出登录',
      content: '确定退出当前账号？',
      success: (r) => {
        if (r.confirm) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          app.globalData.userInfo = null
          wx.reLaunch({ url: '/pages/login/login' })
        }
      }
    })
  }
})

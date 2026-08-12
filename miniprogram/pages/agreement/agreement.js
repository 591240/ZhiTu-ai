Page({
  data: {
    tab: 'privacy' // privacy / user
  },
  switchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab })
  }
})

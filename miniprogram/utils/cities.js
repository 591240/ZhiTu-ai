// utils/cities.js —— 目的地城市常量
// 之前这份列表住在 utils/mock.js 里，导致「关掉 mock」后城市选择器跟着一起消失。
// 城市列表是产品数据，不是演示数据，单独放这里。

// 首页城市选择器展示的城市（与后端 kb 语料 / 城市封面图保持一致）
const CITIES = [
  { name: '杭州', province: '浙江', hot: true },
  { name: '北京', province: '北京', hot: true },
  { name: '上海', province: '上海', hot: true },
  { name: '成都', province: '四川', hot: true },
  { name: '西安', province: '陕西', hot: true },
  { name: '重庆', province: '重庆', hot: true },
  { name: '厦门', province: '福建', hot: true },
  { name: '苏州', province: '江苏', hot: true },
  { name: '南京', province: '江苏', hot: false },
  { name: '长沙', province: '湖南', hot: false },
  { name: '青岛', province: '山东', hot: false },
  { name: '武汉', province: '湖北', hot: false },
  { name: '广州', province: '广东', hot: false },
  { name: '深圳', province: '广东', hot: false },
  { name: '三亚', province: '海南', hot: false },
  { name: '丽江', province: '云南', hot: false },
  { name: '大理', province: '云南', hot: false },
  { name: '桂林', province: '广西', hot: false },
  { name: '香港', province: '香港', hot: false },
  { name: '澳门', province: '澳门', hot: false }
]

const CITY_NAMES = CITIES.map(c => c.name)

module.exports = { CITIES, CITY_NAMES }

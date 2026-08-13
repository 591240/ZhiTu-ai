// utils/mock.js —— 本地示例数据与 Mock 接口路由
// 当 env.USE_MOCK=true 时，request 会走这里，无需后端即可演示全部功能。

const mockUser = {
  id: 10001,
  nickname: '微信用户',
  avatar: '',
  city: '杭州',
  isVip: false,
  is_vip: false,
  vipExpireAt: null,
  points: 20
}

// 城市库（含快捷服务跳转的第三方小程序 appid 占位）
const mockCities = [
  { name: '杭州', province: '浙江', hot: true },
  { name: '成都', province: '四川', hot: true },
  { name: '西安', province: '陕西', hot: true },
  { name: '苏州', province: '江苏', hot: true },
  { name: '重庆', province: '重庆', hot: true },
  { name: '厦门', province: '福建', hot: true },
  { name: '长沙', province: '湖南', hot: true },
  { name: '南京', province: '江苏', hot: true }
]

// 预置景点库：按城市+风格给出每日景点/餐饮/交通
const SPOTS = {
  '杭州': {
    popular: [
      [
        { name: '西湖', address: '杭州市西湖区龙井路1号', time_slot: 'morning', duration_min: 180, ticket_price: 0, category: '自然风光', description: '断桥残雪、苏堤春晓，建议骑行或步行环湖。' },
        { name: '灵隐寺', address: '杭州市西湖区法云弄1号', time_slot: 'afternoon', duration_min: 150, ticket_price: 75, need_booking: true, official_account: '灵隐寺', category: '人文历史', description: '千年古刹，需先买飞来峰门票再入寺。' }
      ],
      [
        { name: '西溪湿地', address: '杭州市西湖区天目山路518号', time_slot: 'morning', duration_min: 150, ticket_price: 80, category: '自然风光', description: '城市湿地，摇橹船体验最佳。' },
        { name: '河坊街', address: '杭州市上城区河坊街', time_slot: 'evening', duration_min: 120, ticket_price: 0, category: '美食', description: '老字号小吃与伴手礼集中地。' }
      ]
    ],
    niche: [
      [
        { name: '九溪烟树', address: '杭州市西湖区九溪路', time_slot: 'morning', duration_min: 160, ticket_price: 0, category: '自然风光', description: '本地人私藏徒步路线，林荫溪水。' },
        { name: '良渚古城遗址', address: '杭州市余杭区瓶窑镇', time_slot: 'afternoon', duration_min: 160, ticket_price: 0, category: '人文历史', description: '世界遗产，人少清静。' }
      ],
      [
        { name: '龙井村', address: '杭州市西湖区龙井村', time_slot: 'morning', duration_min: 140, ticket_price: 0, category: '休闲度假', description: '采茶品茗，避开人流。' },
        { name: '馒头山社区', time_slot: 'evening', duration_min: 100, ticket_price: 0, category: '人文历史', description: '老杭州烟火气，摄影爱好者聚集。' }
      ]
    ],
    meals: [
      { name: '外婆家', type: 'lunch', avg_price: 80, specialty: '茶香鸡、麻婆豆腐', address: '多家分店' },
      { name: '楼外楼', type: 'dinner', avg_price: 160, specialty: '西湖醋鱼、龙井虾仁', address: '孤山路30号' },
      { name: '知味观', type: 'breakfast', avg_price: 30, specialty: '猫耳朵、小笼', address: '仁和路83号' }
    ]
  },
  '成都': {
    popular: [
      [
        { name: '宽窄巷子', address: '成都市青羊区金河路口', time_slot: 'morning', duration_min: 150, ticket_price: 0, category: '人文历史', description: '老成都院落文化代表。' },
        { name: '锦里', address: '成都市武侯区武侯祠大街231号', time_slot: 'evening', duration_min: 120, ticket_price: 0, category: '美食', description: '三国文化+小吃街。' }
      ],
      [
        { name: '大熊猫繁育研究基地', address: '成都市成华区熊猫大道1375号', time_slot: 'morning', duration_min: 200, ticket_price: 55, need_booking: true, official_account: '成都熊猫基地', category: '亲子', description: '早上8点前到可看饲养员喂熊猫。' },
        { name: '武侯祠', address: '成都市武侯区武侯祠大街231号', time_slot: 'afternoon', duration_min: 120, ticket_price: 50, need_booking: false, official_account: '成都武侯祠', category: '人文历史', description: '中国唯一的君臣合祀祠庙。' }
      ],
      [
        { name: '春熙路', address: '成都市锦江区春熙路', time_slot: 'afternoon', duration_min: 150, ticket_price: 0, category: '网红打卡', description: '太古里+IFS爬墙熊猫。' }
      ]
    ],
    niche: [
      [
        { name: '玉林路小酒馆', address: '成都市武侯区玉林西路', time_slot: 'evening', duration_min: 120, ticket_price: 0, category: '休闲度假', description: '赵雷歌声里的小巷，文艺青年聚集。' },
        { name: '东郊记忆', address: '成都市成华区建设南支路', time_slot: 'morning', duration_min: 150, ticket_price: 0, category: '人文历史', description: '旧工厂改造的文创园。' }
      ],
      [
        { name: '彭镇老茶馆', address: '成都市双流区彭镇', time_slot: 'morning', duration_min: 160, ticket_price: 0, category: '人文历史', description: '百年茶馆，老茶客与摄影人。' }
      ],
      [
        { name: '麓湖生态城', address: '成都市天府新区', time_slot: 'afternoon', duration_min: 160, ticket_price: 0, category: '自然风光', description: '水上建筑与艺术展。' }
      ]
    ],
    meals: [
      { name: '小龙坎火锅', type: 'dinner', avg_price: 120, specialty: '牛油锅底、毛肚', address: '多家分店' },
      { name: '陈麻婆豆腐', type: 'lunch', avg_price: 70, specialty: '麻婆豆腐、回锅肉', address: '青华路' },
      { name: '甜水面', type: 'breakfast', avg_price: 20, specialty: '甜辣面条', address: '街边小吃' }
    ]
  }
}

const GENERIC = {
  popular: [
    [
      { name: '{city}博物馆', address: '{city}市中心', time_slot: 'morning', duration_min: 150, ticket_price: 0, category: '人文历史', description: '了解城市历史的好去处。' },
      { name: '{city}中央公园', address: '{city}新区', time_slot: 'afternoon', duration_min: 140, ticket_price: 0, category: '自然风光', description: '城市绿肺，适合散步。' }
    ],
    [
      { name: '{city}老街', address: '{city}老城区', time_slot: 'evening', duration_min: 120, ticket_price: 0, category: '美食', description: '本地小吃与夜市。' }
    ]
  ],
  niche: [
    [
      { name: '{city}近郊徒步线', address: '{city}郊外', time_slot: 'morning', duration_min: 200, ticket_price: 0, category: '自然风光', description: '避开人流的秘境路线。' }
    ],
    [
      { name: '{city}独立书店', address: '{city}文艺街区', time_slot: 'afternoon', duration_min: 120, ticket_price: 0, category: '休闲度假', description: '城市文化角落。' }
    ]
  ],
  meals: [
    { name: '{city}特色菜馆', type: 'lunch', avg_price: 80, specialty: '本地招牌菜', address: '市中心' },
    { name: '{city}夜市', type: 'dinner', avg_price: 60, specialty: '街头小吃', address: '老城区' }
  ]
}

function fill(tpl, city) { return JSON.parse(JSON.stringify(tpl).replace(/\{city\}/g, city)) }

// 给景点附加封面图（按景点名取稳定真实照片）
function attachImage(spot) {
  const s = Object.assign({}, spot)
  s.image = `https://loremflickr.com/600/400/${encodeURIComponent(spot.name)}?lock=${(function (str) { let h = 0; for (let i = 0; i < str.length; i++) { h = (h << 5) - h + str.charCodeAt(i); h |= 0 } return Math.abs(h) % 1000 })(spot.name)}`
  return s
}

// 按参数生成结构化行程
function genTrip(p) {
  const city = p.city || '杭州'
  const days = Math.min(Math.max(parseInt(p.days) || 2, 1), 4)
  const routeType = p.route_type === 'niche' ? 'niche' : 'popular'
  const repo = SPOTS[city] ? SPOTS[city] : null
  const base = repo ? repo : GENERIC
  const dayPlans = (routeType === 'niche' ? base.niche : base.popular)
  const meals = repo ? repo.meals : base.meals

  const budgetMin = parseInt(p.budget_min) || 500
  let budgetMax = parseInt(p.budget_max) || 1500
  if (budgetMax < budgetMin) budgetMax = budgetMin
  const perDayAvg = Math.floor((budgetMin + budgetMax) / 2 / days)

  const itinerary = []
  let total = 0
  // AI 预估渠道（mock 演示用，按名称稳定分配）
  const ticketCh = ['景区官方', '美团', '抖音团购', '携程']
  const dealCh = ['美团', '抖音团购', '大众点评']
  const pick = (arr, s) => { let h = 0; for (let i = 0; i < s.length; i++) { h = (h << 5) - h + s.charCodeAt(i); h |= 0 } return arr[Math.abs(h) % arr.length] }
  for (let i = 1; i <= days; i++) {
    const plan = dayPlans[(i - 1) % dayPlans.length]
    const spots = (repo ? plan : fill(plan, city)).map(attachImage).map(s => {
      s.best_price = s.ticket_price
      if (s.ticket_price > 0) s.ticket_channel = s.official_account ? '景区官方' : pick(ticketCh, s.name)
      return s
    })
    const dayMeals = meals.slice((i - 1) * 1, (i - 1) * 1 + 2).map(m => repo ? m : fill(m, city)).map(m => {
      m.deal_channel = pick(dealCh, m.name)
      return m
    })
    const budget = Math.max(100, perDayAvg + (i % 3 - 1) * 30)
    total += budget
    itinerary.push({
      day_number: i,
      date_label: ['一', '二', '三', '四'][i - 1] ? `第${['一', '二', '三', '四'][i - 1]}天` : `第${i}天`,
      spots,
      meals: dayMeals,
      transport: [
        { from: '酒店', to: spots[0].name, mode: p.transport_mode || '地铁', duration_min: 30, cost: 5 }
      ],
      budget,
      tips: i === 1 ? '• 出行前查看天气，备好舒适鞋\n• 热门景点建议错峰前往' : '• 注意保管随身物品\n• 用餐可参考本地人排队店铺'
    })
  }

  const title = `${city}${days}日${routeType === 'niche' ? '小众深度' : '经典大众'}游`
  return {
    title,
    city,
    days,
    route_type: routeType,
    crowd_type: p.crowd_type || '朋友',
    budget_min: budgetMin,
    budget_max: budgetMax,
    budget_level: budgetMax < 500 ? '经济' : budgetMax > 1500 ? '高端' : '舒适',
    content: { itinerary, total_budget: total, budget_analysis: `预估人均总花费约 ¥${total}，按您设置的 ¥${budgetMin}-¥${budgetMax}/人预算规划。`, preparations: crossBorderPreparations(city) }
  }
}

// 跨境/特殊地区行前准备（mock 预览用）
function crossBorderPreparations(city) {
  const c = (city || '').replace('{city}', '').trim()
  if (c.includes('香港')) {
    return [
      { icon: '🛂', title: '办理港澳通行证及签注', detail: '需持有效港澳通行证并办理赴港签注（G签/L签），建议提前10个工作日办理。' },
      { icon: '📱', title: '电话卡 / 漫游', detail: '提前开通港澳台漫游或购买香港本地电话卡，确保地图、打车、导航可用。' },
      { icon: '💳', title: '货币与支付', detail: '香港使用港币，八达通/支付宝香港/微信香港钱包通用，建议备少量现金。' },
      { icon: '🔌', title: '转换插头', detail: '英标插头，电压220V，出行前备好转换头。' }
    ]
  }
  if (c.includes('澳门')) {
    return [
      { icon: '🛂', title: '办理港澳通行证及签注', detail: '需持有效港澳通行证并办理赴澳签注，建议提前10个工作日办理。' },
      { icon: '📱', title: '电话卡 / 漫游', detail: '提前开通港澳台漫游或购买澳门本地电话卡。' },
      { icon: '💳', title: '货币与支付', detail: '澳门使用澳门元/港币，多数商户支持支付宝微信，建议备少量现金。' },
      { icon: '🔌', title: '转换插头', detail: '英标插头，电压220V，备好转换头。' }
    ]
  }
  if (c.includes('台湾')) {
    return [
      { icon: '🛂', title: '办理入台证', detail: '需大通证+入台证（通过有资质的旅行社办理），提前2-3周准备。' },
      { icon: '📱', title: '电话卡 / 漫游', detail: '开通港澳台漫游或购买台湾本地电话卡。' },
      { icon: '💳', title: '货币与支付', detail: '台湾使用新台币，街口/Line Pay常用，备少量现金。' },
      { icon: '🔌', title: '转换插头', detail: '美标插头，电压110V，需转换头+变压器。' }
    ]
  }
  return []
}

// 预置示例行程（用于"我的行程"列表）
function buildMockTrips() {
  const t1 = genTrip({ city: '杭州', days: 2, route_type: 'popular', crowd_type: '情侣', budget_min: 500, budget_max: 1500 })
  const t2 = genTrip({ city: '成都', days: 3, route_type: 'niche', crowd_type: '朋友', budget_min: 200, budget_max: 500 })
  const t3 = genTrip({ city: '西安', days: 2, route_type: 'popular', crowd_type: '学生', budget_min: 200, budget_max: 500 })
  const t4 = genTrip({ city: '香港', days: 3, route_type: 'popular', crowd_type: '家庭', budget_min: 1500, budget_max: 3000 })
  const now = Date.now()
  const mk = (trip, id, status, offset) => ({
    id, title: trip.title, city: trip.city, days: trip.days,
    route_type: trip.route_type, crowd_type: trip.crowd_type,
    budget_level: trip.budget_level, total_budget: trip.content.total_budget,
    status, created_at: now - offset, content: trip.content
  })
  return [
    mk(t1, 't1001', 'active', 3600000),
    mk(t2, 't1002', 'active', 86400000),
    mk(t4, 't1004', 'active', 86400000 * 2),
    mk(t3, 't1003', 'archived', 86400000 * 5)
  ]
}

const MOCK_TRIPS = buildMockTrips()

// 预置模板广场
const MOCK_TEMPLATES = [
  { id: 'tp01', title: '杭州2日经典西湖游', city: '杭州', days: 2, spots_count: 6, uses: 1280, route_type: 'popular', cover: '🏞️', content: genTrip({ city: '杭州', days: 2, route_type: 'popular' }).content },
  { id: 'tp02', title: '成都3日小众文艺游', city: '成都', days: 3, spots_count: 7, uses: 860, route_type: 'niche', cover: '🐼', content: genTrip({ city: '成都', days: 3, route_type: 'niche' }).content },
  { id: 'tp03', title: '西安2日美食历史游', city: '西安', days: 2, spots_count: 5, uses: 2100, route_type: 'popular', cover: '🏯', content: genTrip({ city: '西安', days: 2, route_type: 'popular' }).content },
  { id: 'tp04', title: '苏州1日园林精华游', city: '苏州', days: 1, spots_count: 4, uses: 540, route_type: 'popular', cover: '🌿', content: genTrip({ city: '苏州', days: 1, route_type: 'popular' }).content }
]

// 会员套餐
const MOCK_PLANS = [
  {
    type: 'month', name: '月度会员', price: 19.9, original: 0, period: '1 个月',
    benefits: ['无限次 AI 行程生成', '大众 + 小众双路线', '对话微调行程', '行李清单 + 美食红黑榜', '模板广场无限使用']
  },
  {
    type: 'year', name: '年度会员', price: 129, original: 238, period: '12 个月', tag: '超值',
    benefits: ['包含月度会员全部权益', '平均每月仅 10.7 元', '优先体验新功能', '专属客服']
  }
]

// 用户收藏的模板（初始示例）
const MOCK_COLLECTIONS = ['tp03']

// 简易问答库
function fakeQA(q) {
  const text = (q || '').toLowerCase()
  if (text.includes('西湖')) return '西湖全天免费开放，建议清晨或傍晚前往人少景美；核心景点有断桥、苏堤、雷峰塔（登塔需门票40元）。'
  if (text.includes('避雷') || text.includes('坑')) return '避坑提示：①景区门口拉客的"低价团"勿信；②网红餐厅排队久可错峰；③打车用平台叫车，别上黑车。'
  if (text.includes('行李') || text.includes('打包')) return '行李清单已生成，请查看下方清单卡片。'
  return '已收到你的问题。作为行程助手，我可以帮你查询目的地美食、景区开放时间、避坑建议和行李清单，请描述更具体的需求～'
}

// Mock 接口路由：返回 { code, data, message }
function handleMock(url, method, data) {
  data = data || {}
  if (url.includes('/auth/login')) {
    return { code: 0, data: { token: 'mock-token-' + Date.now(), user: mockUser }, message: 'ok' }
  }
  if (url.includes('/user/info') || url.includes('/user/me')) {
    return { code: 0, data: mockUser, message: 'ok' }
  }
  if (url.includes('/user/stats')) {
    return { code: 0, data: { tripCount: MOCK_TRIPS.length, cityCount: 6 }, message: 'ok' }
  }
  if (url.includes('/user/points')) {
    return { code: 0, data: { points: mockUser.points }, message: 'ok' }
  }
  if (url.includes('/user/recharge')) {
    return { code: 0, data: { message: '充值申请已提交，请扫码支付后联系客服加积分' }, message: 'ok' }
  }
  if (url.includes('/trip/list')) {
    const status = data.status
    let list = MOCK_TRIPS
    if (status === 'active') list = list.filter(t => t.status === 'active')
    // 合并本地保存的行程
    const local = wx.getStorageSync('localTrips') || []
    list = list.concat(local)
    return { code: 0, data: { list }, message: 'ok' }
  }
  if (url.includes('/trip/detail')) {
    const all = MOCK_TRIPS.concat(wx.getStorageSync('localTrips') || [])
    const t = all.find(x => x.id === data.id)
    return { code: 0, data: { trip: t || MOCK_TRIPS[0] }, message: 'ok' }
  }
  if (url.includes('/trip/save')) {
    const local = wx.getStorageSync('localTrips') || []
    const trip = { ...data.trip, id: 'loc' + Date.now(), created_at: Date.now(), status: 'active' }
    local.unshift(trip)
    wx.setStorageSync('localTrips', local)
    return { code: 0, data: { id: trip.id }, message: 'ok' }
  }
  if (url.includes('/trip/delete')) {
    let local = wx.getStorageSync('localTrips') || []
    local = local.filter(t => t.id !== data.id)
    wx.setStorageSync('localTrips', local)
    return { code: 0, data: {}, message: 'ok' }
  }
  if (url.includes('/plan/form') || url.includes('/plan/quick')) {
    if (mockUser.points < 10) {
      return { code: 4001, data: null, message: '积分不足，请充值后再生成行程' }
    }
    mockUser.points -= 10
    const trip = genTrip(data)
    return { code: 0, data: { trip: { id: 'gen' + Date.now(), ...trip } }, message: 'ok' }
  }
  if (url.includes('/plan/chat-adjust')) {
    // 微调：在现有行程上加一条晚餐建议
    const trip = data.trip || MOCK_TRIPS[0]
    const content = JSON.parse(JSON.stringify(trip.content))
    const lastDay = content.itinerary[content.itinerary.length - 1]
    lastDay.meals = lastDay.meals || []
    lastDay.meals.push({ name: '当地特色夜宵', type: 'dinner', avg_price: 60, specialty: '根据指令新增', address: trip.city })
    return { code: 0, data: { trip: { ...trip, content } }, message: 'ok' }
  }
  if (url.includes('/template/hot')) {
    return { code: 0, data: { list: MOCK_TEMPLATES }, message: 'ok' }
  }
  if (url.includes('/template/detail')) {
    const t = MOCK_TEMPLATES.find(x => x.id === data.id) || MOCK_TEMPLATES[0]
    return { code: 0, data: { template: t }, message: 'ok' }
  }
  if (url.includes('/template/use')) {
    const t = MOCK_TEMPLATES.find(x => x.id === data.id) || MOCK_TEMPLATES[0]
    return { code: 0, data: { content: t.content }, message: 'ok' }
  }
  if (url.includes('/chat/qa')) {
    if (mockUser.points < 2) {
      return { code: 4001, data: null, message: '积分不足，请充值后再提问' }
    }
    mockUser.points -= 2
    return { code: 0, data: { answer: fakeQA(data.question) }, message: 'ok' }
  }
  if (url.includes('/chat/luggage')) {
    return { code: 0, data: { list: [
      { group: '衣物', items: ['外套', '舒适运动鞋', '换洗衣物'] },
      { group: '洗漱', items: ['牙刷牙膏', '防晒霜', '护肤品'] },
      { group: '电子', items: ['充电宝', '数据线', '耳机'] },
      { group: '药品', items: ['创可贴', '肠胃药', '晕车药'] }
    ] }, message: 'ok' }
  }
  if (url.includes('/chat/food')) {
    return { code: 0, data: {
      red: ['本地老字号餐馆', '夜市人气小吃', '景区外居民区餐厅'],
      black: ['景区内高价套餐', '拉客低价团餐', '无明码标价大排档']
    }, message: 'ok' }
  }
  if (url.includes('/membership/plans')) {
    return { code: 0, data: { plans: MOCK_PLANS }, message: 'ok' }
  }
  if (url.includes('/membership/order')) {
    mockUser.isVip = true
    const expire = new Date()
    if (data.plan_type === 'year') expire.setFullYear(expire.getFullYear() + 1)
    else expire.setMonth(expire.getMonth() + 1)
    mockUser.vipExpireAt = expire.getTime()
    return { code: 0, data: { order_id: 'ord' + Date.now(), paid: true, vipExpireAt: mockUser.vipExpireAt }, message: 'ok' }
  }
  if (url.includes('/collection/add') || url.includes('/template/collect')) {
    const tid = data.template_id || data.id
    if (tid && !MOCK_COLLECTIONS.includes(tid)) MOCK_COLLECTIONS.push(tid)
    return { code: 0, data: { collected: true }, message: 'ok' }
  }
  if (url.includes('/collection/list')) {
    const list = MOCK_TEMPLATES.filter(t => MOCK_COLLECTIONS.includes(t.id))
    return { code: 0, data: { list }, message: 'ok' }
  }
  if (url.includes('/template/published') || url.includes('/published/list')) {
    return { code: 0, data: { list: [MOCK_TEMPLATES[1], MOCK_TEMPLATES[3]] }, message: 'ok' }
  }
  if (url.includes('/ocr/recognize')) {
    const trip = genTrip({ city: '杭州', days: 2, route_type: 'popular' })
    return { code: 0, data: {
      recognized: { city: '杭州', days: 2, spots: ['西湖', '灵隐寺', '河坊街'] },
      trip: { id: 'ocr' + Date.now(), ...trip }
    }, message: 'ok' }
  }
  if (url.includes('/ticket/search')) {
    const date = data.date || new Date().toISOString().slice(0, 10)
    const from = data.from_station || '北京'
    const to = data.to_station || '杭州'
    const type = data.train_type || ''
    const allTrains = [
      { trainNo: 'G31', line: 'G31 北京南 06:30 杭州东 12:30 历时6小时0分 二等座¥626 一等座¥1001', depart: '06:30', arrive: '12:30', duration: '6h0m', prices: ['626', '1001'] },
      { trainNo: 'G33', line: 'G33 北京南 07:40 杭州东 13:35 历时5小时55分 二等座¥626 一等座¥1001', depart: '07:40', arrive: '13:35', duration: '5h55m', prices: ['626', '1001'] },
      { trainNo: 'G35', line: 'G35 北京南 09:10 杭州东 15:05 历时5小时55分 二等座¥626 一等座¥1001', depart: '09:10', arrive: '15:05', duration: '5h55m', prices: ['626', '1001'] },
      { trainNo: 'G163', line: 'G163 北京南 11:45 杭州东 18:25 历时6小时40分 二等座¥626 一等座¥1001', depart: '11:45', arrive: '18:25', duration: '6h40m', prices: ['626', '1001'] },
      { trainNo: 'D711', line: 'D711 北京南 13:25 杭州东 21:40 历时8小时15分 二等座¥408 一等座¥654', depart: '13:25', arrive: '21:40', duration: '8h15m', prices: ['408', '654'] },
      { trainNo: 'K101', line: 'K101 北京 23:20 杭州南 18:50 历时19小时30分 硬座¥192 硬卧¥328', depart: '23:20', arrive: '18:50', duration: '19h30m', prices: ['192', '328'] }
    ]
    let trains = allTrains
    if (type) {
      trains = allTrains.filter(t => t.trainNo.startsWith(type))
    }
    return { code: 0, data: {
      source: '12306-mcp',
      date,
      from,
      to,
      trains,
      raw: trains.map(t => t.line).join('\n')
    }, message: 'ok' }
  }
  if (url.includes('/map/geocode-batch')) {
    const names = ((data.names || '')).split(',').filter(Boolean)
    const table = {
      '西湖': [30.2592, 120.1490], '灵隐寺': [30.2410, 120.0990], '西溪湿地': [30.2700, 120.0700],
      '河坊街': [30.2430, 120.1700], '九溪烟树': [30.2100, 120.1200], '良渚古城遗址': [30.4000, 119.9800],
      '龙井村': [30.2100, 120.1300], '断桥': [30.2595, 120.1485], '苏堤': [30.2450, 120.1450],
      '雷峰塔': [30.2310, 120.1480], '千岛湖': [29.6000, 119.0400],
      '宽窄巷子': [30.6690, 104.0560], '锦里': [30.6420, 104.0450], '武侯祠': [30.6420, 104.0450],
      '大熊猫繁育研究基地': [30.7330, 104.1460], '春熙路': [30.6570, 104.0810], '玉林路小酒馆': [30.6320, 104.0930],
      '东郊记忆': [30.6700, 104.1100], '杜甫草堂': [30.6590, 104.0280], '金沙遗址': [30.6820, 104.0100],
      '都江堰': [31.0040, 103.6180], '青城山': [30.9000, 103.5660],
      '杭州': [30.2741, 120.1551], '杭州东站': [30.2741, 120.2120], '杭州东': [30.2741, 120.2120],
      '北京': [39.9042, 116.4074], '北京南站': [39.8657, 116.3786], '北京南': [39.8657, 116.3786],
      '上海': [31.2304, 121.4737], '上海虹桥站': [31.1942, 121.3199], '上海虹桥': [31.1942, 121.3199],
      '成都': [30.5728, 104.0668], '广州': [23.1291, 113.2644], '深圳': [22.5431, 114.0579],
      '西安': [34.3416, 108.9398], '武汉': [30.5928, 114.3055], '南京': [32.0603, 118.7969],
      '长沙': [28.2282, 112.9388], '重庆': [29.5630, 106.5516], '厦门': [24.4798, 118.0894],
      '外婆家': [30.2741, 120.1551], '楼外楼': [30.2590, 120.1450], '知味观': [30.2580, 120.1650],
      '小龙坎火锅': [30.6570, 104.0810], '陈麻婆豆腐': [30.6590, 104.0280], '甜水面': [30.6570, 104.0810]
    }
    const results = names.map((n) => {
      const c = table[n] || table[n.replace(/站$/, '')]
      return c ? { lat: c[0], lng: c[1], name: n, address: n, source: 'builtin' } : null
    })
    return { code: 0, data: { results }, message: 'ok' }
  }
  if (url.includes('/map/geocode')) {
    const name = data.name || '杭州'
    const table = {
      '西湖': [30.2592, 120.1490], '灵隐寺': [30.2410, 120.0990], '西溪湿地': [30.2700, 120.0700],
      '河坊街': [30.2430, 120.1700], '九溪烟树': [30.2100, 120.1200], '良渚古城遗址': [30.4000, 119.9800],
      '龙井村': [30.2100, 120.1300], '断桥': [30.2595, 120.1485], '苏堤': [30.2450, 120.1450],
      '雷峰塔': [30.2310, 120.1480], '千岛湖': [29.6000, 119.0400],
      '宽窄巷子': [30.6690, 104.0560], '锦里': [30.6420, 104.0450], '武侯祠': [30.6420, 104.0450],
      '大熊猫繁育研究基地': [30.7330, 104.1460], '春熙路': [30.6570, 104.0810], '玉林路小酒馆': [30.6320, 104.0930],
      '东郊记忆': [30.6700, 104.1100], '杜甫草堂': [30.6590, 104.0280], '金沙遗址': [30.6820, 104.0100],
      '都江堰': [31.0040, 103.6180], '青城山': [30.9000, 103.5660],
      '杭州': [30.2741, 120.1551], '杭州东站': [30.2741, 120.2120], '杭州东': [30.2741, 120.2120],
      '北京': [39.9042, 116.4074], '北京南站': [39.8657, 116.3786], '北京南': [39.8657, 116.3786],
      '上海': [31.2304, 121.4737], '上海虹桥站': [31.1942, 121.3199], '上海虹桥': [31.1942, 121.3199],
      '成都': [30.5728, 104.0668], '广州': [23.1291, 113.2644], '深圳': [22.5431, 114.0579],
      '西安': [34.3416, 108.9398], '武汉': [30.5928, 114.3055], '南京': [32.0603, 118.7969],
      '长沙': [28.2282, 112.9388], '重庆': [29.5630, 106.5516], '厦门': [24.4798, 118.0894],
      '外婆家': [30.2741, 120.1551], '楼外楼': [30.2590, 120.1450], '知味观': [30.2580, 120.1650],
      '小龙坎火锅': [30.6570, 104.0810], '陈麻婆豆腐': [30.6590, 104.0280], '甜水面': [30.6570, 104.0810]
    }
    const c = table[name] || table[name.replace(/站$/, '')] || [30.2741, 120.1551]
    return { code: 0, data: { lat: c[0], lng: c[1], name, address: name, source: 'builtin' }, message: 'ok' }
  }
  // 默认
  return { code: 0, data: {}, message: 'ok' }
}

module.exports = {
  mockUser,
  mockCities,
  MOCK_TRIPS,
  MOCK_TEMPLATES,
  genTrip,
  handleMock,
  fakeQA
}

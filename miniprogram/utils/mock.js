// utils/mock.js —— 本地示例数据与 Mock 接口路由
// 当 env.USE_MOCK=true 时，request 会走这里，无需后端即可演示全部功能。

const { monetizationEnabled } = require('./features')

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

// 预置景点库：按城市+风格给出每日景点/餐饮/交通（本地演示用，内容经过核对）
const SPOTS = {
  "杭州": {
    "popular": [
      [
        {
          "name": "西湖",
          "address": "杭州市西湖区龙井路1号",
          "time_slot": "morning",
          "duration_min": 180,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "断桥残雪、苏堤春晓，建议骑行或步行环湖，清晨人少景美。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "断桥残雪",
              "best_time": "清晨/黄昏",
              "tip": "低角度拍湖面反光更有层次",
              "avoid_crowd": "开园前30分钟抵达",
              "day_night": "日",
              "suitable_for": "所有人"
            },
            {
              "position": "雷峰塔顶层",
              "best_time": "日落",
              "tip": "俯拍西湖全景与城郭",
              "avoid_crowd": "避开周末傍晚",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "灵隐寺",
          "address": "杭州市西湖区法云弄1号",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 75,
          "category": "人文历史",
          "description": "千年古刹，需先买飞来峰门票再入寺，寺内素面值得一试。",
          "need_booking": true,
          "official_account": "灵隐寺",
          "photo_spots": [
            {
              "position": "大雄宝殿前广场",
              "best_time": "上午",
              "tip": "顺光拍古建筑飞檐",
              "avoid_crowd": "9点前入寺",
              "day_night": "日",
              "suitable_for": "所有人"
            },
            {
              "position": "永福寺茶室",
              "best_time": "下午",
              "tip": "借庭院框景构图",
              "avoid_crowd": "工作日上午",
              "day_night": "日",
              "suitable_for": "亲子"
            }
          ]
        }
      ],
      [
        {
          "name": "西溪湿地",
          "address": "杭州市西湖区天目山路518号",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 80,
          "category": "自然风光",
          "description": "城市湿地，摇橹船体验最佳，深秋芦花似雪。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "烟水渔庄",
              "best_time": "上午",
              "tip": "拍芦苇与水道",
              "avoid_crowd": "开园首小时",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "河坊街",
          "address": "杭州市上城区河坊街",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "老字号小吃与伴手礼集中地，定胜糕、葱包桧必尝。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "清河坊牌坊",
              "best_time": "夜晚",
              "tip": "拍红灯笼长街",
              "avoid_crowd": "19点后亮灯",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "宋城",
          "address": "杭州市之江路148号",
          "time_slot": "morning",
          "duration_min": 180,
          "ticket_price": 320,
          "category": "休闲度假",
          "description": "大型千古情演出+市井街景，适合家庭一日游。",
          "need_booking": true,
          "official_account": "宋城演艺",
          "photo_spots": [
            {
              "position": "清明上河图电影馆",
              "best_time": "下午",
              "tip": "室内光影适合人像",
              "avoid_crowd": "演出前入场",
              "day_night": "日",
              "suitable_for": "家庭"
            }
          ]
        },
        {
          "name": "京杭大运河·拱宸桥",
          "address": "杭州市拱墅区拱宸桥",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "桥西历史街区夜游，博物馆群与手工艺活态展示。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "拱宸桥顶",
              "best_time": "夜晚",
              "tip": "拍运河灯影",
              "avoid_crowd": "20点后",
              "day_night": "夜",
              "suitable_for": "摄影爱好者"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "九溪烟树",
          "address": "杭州市西湖区九溪路",
          "time_slot": "morning",
          "duration_min": 160,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "本地人私藏徒步路线，林荫溪水，秋天最美。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "九溪烟树亭",
              "best_time": "上午",
              "tip": "拍雾气与红叶",
              "avoid_crowd": "雨后清晨",
              "day_night": "日",
              "suitable_for": "徒步爱好者"
            }
          ]
        },
        {
          "name": "良渚古城遗址",
          "address": "杭州市余杭区瓶窑镇",
          "time_slot": "afternoon",
          "duration_min": 160,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "世界遗产，人少清静，鹿苑与稻田很出片。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "莫角山台地",
              "best_time": "下午",
              "tip": "拍稻田与远山",
              "avoid_crowd": "工作日",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "龙井村",
          "address": "杭州市西湖区龙井村",
          "time_slot": "morning",
          "duration_min": 140,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "采茶品茗，避开人流，茶农家可体验炒茶。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "茶园步道",
              "best_time": "上午",
              "tip": "拍采茶人与茶垄",
              "avoid_crowd": "春季采茶季",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "馒头山社区",
          "address": "杭州市上城区馒头山",
          "time_slot": "evening",
          "duration_min": 100,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "老杭州烟火气，凤凰山脚下的市井生活。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "梵天寺经幢",
              "best_time": "傍晚",
              "tip": "拍老巷与夕照",
              "avoid_crowd": "17点后",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "知味观",
        "type": "breakfast",
        "avg_price": 30,
        "specialty": "猫耳朵、小笼",
        "address": "仁和路83号"
      },
      {
        "name": "外婆家",
        "type": "lunch",
        "avg_price": 80,
        "specialty": "茶香鸡、麻婆豆腐",
        "address": "多家分店"
      },
      {
        "name": "楼外楼",
        "type": "dinner",
        "avg_price": 160,
        "specialty": "西湖醋鱼、龙井虾仁",
        "address": "孤山路30号"
      }
    ]
  },
  "成都": {
    "popular": [
      [
        {
          "name": "宽窄巷子",
          "address": "成都市青羊区金河路口",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "老成都院落文化代表，喝茶掏耳体验慢生活。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "井巷子砖墙",
              "best_time": "上午",
              "tip": "拍文化墙与青砖",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "锦里",
          "address": "成都市武侯区武侯祠大街231号",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "三国文化+小吃街，三大炮、糖油果子现做现卖。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "锦里戏台",
              "best_time": "夜晚",
              "tip": "拍红灯笼与戏台",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "大熊猫繁育研究基地",
          "address": "成都市成华区熊猫大道1375号",
          "time_slot": "morning",
          "duration_min": 200,
          "ticket_price": 55,
          "category": "亲子",
          "description": "早上8点前到可看饲养员喂熊猫，幼年熊猫最活跃。",
          "need_booking": true,
          "official_account": "成都熊猫基地",
          "photo_spots": [
            {
              "position": "月亮产房",
              "best_time": "上午",
              "tip": "拍熊猫幼崽",
              "avoid_crowd": "8:30前",
              "day_night": "日",
              "suitable_for": "亲子"
            },
            {
              "position": "熊猫塔",
              "best_time": "上午",
              "tip": "俯拍园区",
              "avoid_crowd": "避开团队",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "武侯祠",
          "address": "成都市武侯区武侯祠大街231号",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 50,
          "category": "人文历史",
          "description": "中国唯一的君臣合祀祠庙，红墙竹影是出片机位。",
          "need_booking": false,
          "official_account": "成都武侯祠",
          "photo_spots": [
            {
              "position": "红墙竹影道",
              "best_time": "下午",
              "tip": "拍对称红墙",
              "avoid_crowd": "14点后光影",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        }
      ],
      [
        {
          "name": "春熙路·太古里",
          "address": "成都市锦江区中纱帽街8号",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "太古里开放式街区+IFS爬墙熊猫，潮牌与川西元素混搭。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "IFS屋顶熊猫",
              "best_time": "下午",
              "tip": "拍人与熊猫合影",
              "avoid_crowd": "16点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "玉林路小酒馆",
          "address": "成都市武侯区玉林西路",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "赵雷歌声里的小巷，文艺青年聚集，夜生活刚刚好。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "小酒馆门口",
              "best_time": "夜晚",
              "tip": "拍霓虹与路人",
              "avoid_crowd": "21点后",
              "day_night": "夜",
              "suitable_for": "年轻人"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "东郊记忆",
          "address": "成都市成华区建设南支路",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "旧工厂改造的文创园，火车头广场与涂鸦墙很潮。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "火车头广场",
              "best_time": "上午",
              "tip": "拍工业风",
              "avoid_crowd": "工作日上午",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "玉林路小酒馆",
          "address": "成都市武侯区玉林西路",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "老社区里的live house与精酿，本地音乐人常驻。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "巷口老树",
              "best_time": "夜晚",
              "tip": "拍市井夜色",
              "avoid_crowd": "20点后",
              "day_night": "夜",
              "suitable_for": "年轻人"
            }
          ]
        }
      ],
      [
        {
          "name": "彭镇老茶馆",
          "address": "成都市双流区彭镇",
          "time_slot": "morning",
          "duration_min": 160,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "百年茶馆，老茶客与摄影人，一碗茶可以坐一上午。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "老虎灶前",
              "best_time": "上午",
              "tip": "拍市井烟火",
              "avoid_crowd": "清晨",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "麓湖生态城",
          "address": "成都市天府新区",
          "time_slot": "afternoon",
          "duration_min": 160,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "水上建筑与艺术展，A4美术馆常设好展。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "水上教堂",
              "best_time": "下午",
              "tip": "拍极简建筑",
              "avoid_crowd": "晴日",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "甜水面",
        "type": "breakfast",
        "avg_price": 20,
        "specialty": "甜辣面条",
        "address": "街边小吃"
      },
      {
        "name": "陈麻婆豆腐",
        "type": "lunch",
        "avg_price": 70,
        "specialty": "麻婆豆腐、回锅肉",
        "address": "青华路"
      },
      {
        "name": "小龙坎火锅",
        "type": "dinner",
        "avg_price": 120,
        "specialty": "牛油锅底、毛肚",
        "address": "多家分店"
      }
    ]
  },
  "西安": {
    "popular": [
      [
        {
          "name": "秦始皇兵马俑",
          "address": "西安市临潼区秦陵北路",
          "time_slot": "morning",
          "duration_min": 210,
          "ticket_price": 120,
          "category": "人文历史",
          "description": "世界第八大奇迹，建议请讲解或租语音导览，一号坑最震撼。",
          "need_booking": true,
          "official_account": "秦始皇帝陵博物院",
          "photo_spots": [
            {
              "position": "一号坑观景台",
              "best_time": "上午",
              "tip": "拍军阵全景",
              "avoid_crowd": "开馆即入",
              "day_night": "日",
              "suitable_for": "所有人"
            },
            {
              "position": "三号坑",
              "best_time": "上午",
              "tip": "拍指挥中心布局",
              "avoid_crowd": "错峰",
              "day_night": "日",
              "suitable_for": "历史爱好者"
            }
          ]
        },
        {
          "name": "华清宫",
          "address": "西安市临潼区华清路38号",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 120,
          "category": "人文历史",
          "description": "唐皇家温泉行宫，《长恨歌》实景演出值得一看。",
          "need_booking": true,
          "official_account": "华清宫",
          "photo_spots": [
            {
              "position": "九龙湖",
              "best_time": "傍晚",
              "tip": "拍宫苑倒影",
              "avoid_crowd": "演出前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "陕西历史博物馆",
          "address": "西安市雁塔区小寨东路91号",
          "time_slot": "morning",
          "duration_min": 180,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "华夏宝库，何家村窖藏与唐俑必看，需提前预约。",
          "need_booking": true,
          "official_account": "陕西历史博物馆",
          "photo_spots": [
            {
              "position": "大厅文物墙",
              "best_time": "上午",
              "tip": "拍青铜器阵列",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "大雁塔·大唐不夜城",
          "address": "西安市雁塔区慈恩路",
          "time_slot": "evening",
          "duration_min": 180,
          "ticket_price": 50,
          "category": "网红打卡",
          "description": "夜游不夜城，不倒翁小姐姐与诗词灯街氛围拉满。",
          "need_booking": false,
          "official_account": "大雁塔",
          "photo_spots": [
            {
              "position": "不夜城中央舞台",
              "best_time": "夜晚",
              "tip": "拍盛世灯街",
              "avoid_crowd": "19:30后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "西安城墙",
          "address": "西安市碑林区南大街",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 54,
          "category": "人文历史",
          "description": "中国现存最完整古城墙，骑行一圈13.7公里约1.5小时。",
          "need_booking": true,
          "official_account": "西安城墙",
          "photo_spots": [
            {
              "position": "永宁门城楼",
              "best_time": "清晨",
              "tip": "拍城门剪影",
              "avoid_crowd": "开城前",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "回民街",
          "address": "西安市莲湖区北院门",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "集中泡馍、烤肉、柿子饼，贾三灌汤包是老字号。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "北院门牌坊",
              "best_time": "夜晚",
              "tip": "拍小吃长街",
              "avoid_crowd": "18点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "小雁塔·西安博物院",
          "address": "西安市碑林区友谊西路",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "人少清静，唐代古塔与庭院很适合慢慢逛。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "荐福寺庭院",
              "best_time": "上午",
              "tip": "拍古塔与古树",
              "avoid_crowd": "工作日上午",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "书院门文化街",
          "address": "西安市碑林区书院门",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "碑林旁的书画街，淘笔墨纸砚与拓片。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "关中书院门楼",
              "best_time": "下午",
              "tip": "拍老街巷",
              "avoid_crowd": "15点后",
              "day_night": "日",
              "suitable_for": "文艺青年"
            }
          ]
        }
      ],
      [
        {
          "name": "大明宫国家遗址公园",
          "address": "西安市未央区自强东路",
          "time_slot": "morning",
          "duration_min": 180,
          "ticket_price": 60,
          "category": "人文历史",
          "description": "盛唐宫殿遗址，开阔如公园，丹凤门遗址馆值得看。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "含元殿台基",
              "best_time": "上午",
              "tip": "拍宫殿轴线",
              "avoid_crowd": "清晨",
              "day_night": "日",
              "suitable_for": "历史爱好者"
            }
          ]
        },
        {
          "name": "永兴坊",
          "address": "西安市新城区中山门",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "非遗美食街区，子长煎饼、柞水糍粑，比回民街更本地。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "非遗戏台",
              "best_time": "夜晚",
              "tip": "拍民俗表演",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "老孙家羊肉泡馍",
        "type": "breakfast",
        "avg_price": 35,
        "specialty": "手掰泡馍",
        "address": "东关正街"
      },
      {
        "name": "长安大牌档",
        "type": "lunch",
        "avg_price": 80,
        "specialty": "葫芦鸡、毛笔酥",
        "address": "多家分店"
      },
      {
        "name": "西安饭庄",
        "type": "dinner",
        "avg_price": 120,
        "specialty": "金线油塔、温拌腰丝",
        "address": "东大街"
      }
    ]
  },
  "苏州": {
    "popular": [
      [
        {
          "name": "拙政园",
          "address": "苏州市姑苏区东北街178号",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 70,
          "category": "人文历史",
          "description": "江南古典园林代表作，借景与框景极致，建议早到。",
          "need_booking": true,
          "official_account": "苏州园林",
          "photo_spots": [
            {
              "position": "远香堂",
              "best_time": "上午",
              "tip": "拍厅堂与荷池",
              "avoid_crowd": "开园即入",
              "day_night": "日",
              "suitable_for": "所有人"
            },
            {
              "position": "小飞虹",
              "best_time": "上午",
              "tip": "拍廊桥倒影",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "苏州博物馆",
          "address": "苏州市姑苏区东北街204号",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "贝聿铭封笔之作，几何光影与片石假山是打卡点。",
          "need_booking": true,
          "official_account": "苏州博物馆",
          "photo_spots": [
            {
              "position": "主庭院片石山房",
              "best_time": "下午",
              "tip": "拍光影假山",
              "avoid_crowd": "14点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "平江路",
          "address": "苏州市姑苏区平江路",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "保留水巷格局的老街，评弹、手作与小吃沿河排开。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "平江路石桥",
              "best_time": "夜晚",
              "tip": "拍水巷灯影",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "虎丘",
          "address": "苏州市姑苏区山门内8号",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 60,
          "category": "自然风光",
          "description": "吴中第一名胜，云岩寺塔斜而不倒，登塔看古城。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "云岩寺塔",
              "best_time": "上午",
              "tip": "拍斜塔与竹林",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "山塘街",
          "address": "苏州市姑苏区山塘街",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "七里山塘，水乡夜色与评弹馆，坐游船更惬意。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "通贵桥",
              "best_time": "傍晚",
              "tip": "拍水乡暮色",
              "avoid_crowd": "17点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "金鸡湖·诚品书店",
          "address": "苏州市工业园区旺墩路",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "现代苏州一面，湖景喷泉与24小时书店。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "湖滨喷泉",
              "best_time": "夜晚",
              "tip": "拍摩天轮与湖景",
              "avoid_crowd": "20点",
              "day_night": "夜",
              "suitable_for": "年轻人"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "留园",
          "address": "苏州市姑苏区留园路338号",
          "time_slot": "morning",
          "duration_min": 140,
          "ticket_price": 45,
          "category": "人文历史",
          "description": "四大名园之一，冠云峰与回廊移步换景。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "冠云峰",
              "best_time": "上午",
              "tip": "拍太湖石玲珑",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "耦园",
          "address": "苏州市姑苏区仓街小新桥巷",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 25,
          "category": "人文历史",
          "description": "夫妻园林，小而精致，几乎无游客。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "城曲草堂",
              "best_time": "下午",
              "tip": "拍临河小窗",
              "avoid_crowd": "工作日",
              "day_night": "日",
              "suitable_for": "文艺青年"
            }
          ]
        }
      ],
      [
        {
          "name": "同里古镇",
          "address": "苏州市吴江区同里镇",
          "time_slot": "morning",
          "duration_min": 200,
          "ticket_price": 100,
          "category": "自然风光",
          "description": "退思园是世界遗产，水乡晨雾极美，可住一晚。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "退思园闹红一舸",
              "best_time": "清晨",
              "tip": "拍水园倒影",
              "avoid_crowd": "7点前",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "本色美术馆",
          "address": "苏州市吴中区通达路",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "临水当代美术馆，周末有市集与茶席。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "美术馆水台",
              "best_time": "傍晚",
              "tip": "拍极简建筑",
              "avoid_crowd": "晴日",
              "day_night": "日",
              "suitable_for": "年轻人"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "哑巴生煎",
        "type": "breakfast",
        "avg_price": 20,
        "specialty": "鲜肉生煎",
        "address": "临顿路"
      },
      {
        "name": "松鹤面馆",
        "type": "lunch",
        "avg_price": 40,
        "specialty": "枫镇大肉面",
        "address": "老字号"
      },
      {
        "name": "得月楼",
        "type": "dinner",
        "avg_price": 150,
        "specialty": "松鼠桂鱼、响油鳝糊",
        "address": "观前街"
      }
    ]
  },
  "重庆": {
    "popular": [
      [
        {
          "name": "解放碑·洪崖洞",
          "address": "重庆市渝中区民族路",
          "time_slot": "morning",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "山城地标，洪崖洞吊脚楼夜景如千与千寻。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "洪崖洞1楼江边",
              "best_time": "夜晚",
              "tip": "拍吊脚楼全景",
              "avoid_crowd": "20点亮灯",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "千厮门大桥",
          "address": "重庆市渝中区千厮门",
          "time_slot": "evening",
          "duration_min": 90,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "步行过桥看两江交汇与渝中夜景，最佳机位之一。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "桥中段",
              "best_time": "夜晚",
              "tip": "拍桥与天际线",
              "avoid_crowd": "21点",
              "day_night": "夜",
              "suitable_for": "摄影爱好者"
            }
          ]
        }
      ],
      [
        {
          "name": "磁器口古镇",
          "address": "重庆市沙坪坝区磁南街",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "千年码头古镇，陈麻花与手工酸辣粉现做现卖。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "古镇正街牌坊",
              "best_time": "上午",
              "tip": "拍老街烟火",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "李子坝轻轨站",
          "address": "重庆市渝中区李子坝",
          "time_slot": "afternoon",
          "duration_min": 90,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "轻轨穿楼奇观，观景平台拍列车进楼。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "观景平台",
              "best_time": "下午",
              "tip": "拍穿楼瞬间",
              "avoid_crowd": "列车到站时",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "鹅岭二厂",
          "address": "重庆市渝中区鹅岭正街",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "旧印刷厂改造文创园，天台看江景日落。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "TESTBED天台",
              "best_time": "傍晚",
              "tip": "拍两江与日落",
              "avoid_crowd": "18点",
              "day_night": "日",
              "suitable_for": "年轻人"
            }
          ]
        }
      ],
      [
        {
          "name": "长江索道",
          "address": "重庆市渝中区新华路",
          "time_slot": "morning",
          "duration_min": 90,
          "ticket_price": 30,
          "category": "休闲度假",
          "description": "空中巴士过江，俯瞰长江与两岸高楼。",
          "need_booking": true,
          "official_account": "长江索道",
          "photo_spots": [
            {
              "position": "索道车厢窗边",
              "best_time": "上午",
              "tip": "拍江景",
              "avoid_crowd": "错峰",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "南山一棵树",
          "address": "重庆市南岸区龙黄公路",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 30,
          "category": "自然风光",
          "description": "俯瞰渝中半岛夜景的制高点，建议傍晚上山。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "观景台",
              "best_time": "夜晚",
              "tip": "拍山城灯海",
              "avoid_crowd": "20点后",
              "day_night": "夜",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "南滨路",
          "address": "重庆市南岸区南滨路",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "江边酒吧与火锅一条街，看对岸璀璨灯火。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "钟楼广场",
              "best_time": "夜晚",
              "tip": "拍对岸天际线",
              "avoid_crowd": "21点",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "山城步道",
          "address": "重庆市渝中区中兴路",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "老重庆生活剖面，悬空栈道与老城墙，本地人散步道。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "悬空栈道",
              "best_time": "上午",
              "tip": "拍梯坎与江",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "徒步爱好者"
            }
          ]
        },
        {
          "name": "黄桷坪涂鸦街",
          "address": "重庆市九龙坡区黄桷坪",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "川美旁整街涂鸦，四川美院老校区也值得逛。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "涂鸦墙前",
              "best_time": "下午",
              "tip": "拍彩色墙",
              "avoid_crowd": "晴日",
              "day_night": "日",
              "suitable_for": "年轻人"
            }
          ]
        }
      ],
      [
        {
          "name": "武隆天生三桥",
          "address": "重庆市武隆区仙女山镇",
          "time_slot": "morning",
          "duration_min": 240,
          "ticket_price": 95,
          "category": "自然风光",
          "description": "喀斯特天坑群，《变形金刚》取景地，建议跟一日游。",
          "need_booking": true,
          "official_account": "武隆景区",
          "photo_spots": [
            {
              "position": "天龙桥",
              "best_time": "上午",
              "tip": "拍天坑与桥",
              "avoid_crowd": "团队前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "桃花源",
          "address": "重庆市酉阳县",
          "time_slot": "afternoon",
          "duration_min": 180,
          "ticket_price": 100,
          "category": "自然风光",
          "description": "陶渊明笔下的秘境，溶洞与世外田园。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "伏羲洞",
              "best_time": "下午",
              "tip": "拍钟乳石",
              "avoid_crowd": "晴日",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "花市豌杂面",
        "type": "breakfast",
        "avg_price": 18,
        "specialty": "豌杂面",
        "address": "解放碑"
      },
      {
        "name": "珮姐老火锅",
        "type": "lunch",
        "avg_price": 130,
        "specialty": "牛油锅底、鲜毛肚",
        "address": "多家分店"
      },
      {
        "name": "周师兄火锅",
        "type": "dinner",
        "avg_price": 140,
        "specialty": "大刀腰片",
        "address": "多家分店"
      }
    ]
  },
  "厦门": {
    "popular": [
      [
        {
          "name": "鼓浪屿",
          "address": "厦门市思明区鼓浪屿",
          "time_slot": "morning",
          "duration_min": 240,
          "ticket_price": 50,
          "category": "自然风光",
          "description": "世界遗产小岛，万国建筑与钢琴之岛，需轮渡上岛。",
          "need_booking": true,
          "official_account": "鼓浪屿",
          "photo_spots": [
            {
              "position": "日光岩顶",
              "best_time": "清晨",
              "tip": "拍全岛与海湾",
              "avoid_crowd": "开船即上岛",
              "day_night": "日",
              "suitable_for": "所有人"
            },
            {
              "position": "菽庄花园",
              "best_time": "上午",
              "tip": "拍园林临海",
              "avoid_crowd": "9点后",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "中山路步行街",
          "address": "厦门市思明区中山路",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "骑楼老街，沙茶面、海蛎煎与伴手礼一条龙。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "骑楼夜景",
              "best_time": "夜晚",
              "tip": "拍霓虹骑楼",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "南普陀寺",
          "address": "厦门市思明区思明南路",
          "time_slot": "morning",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "闽南古刹，素饼出名，可顺登五老峰看厦大。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "大悲殿",
              "best_time": "上午",
              "tip": "拍金色殿宇",
              "avoid_crowd": "8点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "厦门大学·白城沙滩",
          "address": "厦门市思明区思明南路",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "嘉庚风格校舍与白城海滩相连，环岛路骑行起点。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "芙蓉隧道",
              "best_time": "下午",
              "tip": "拍学生涂鸦",
              "avoid_crowd": "15点后",
              "day_night": "日",
              "suitable_for": "年轻人"
            }
          ]
        },
        {
          "name": "曾厝垵",
          "address": "厦门市思明区曾厝垵",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "文艺渔村改造的夜市，民宿与小吃密集。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "村口牌坊",
              "best_time": "夜晚",
              "tip": "拍市集灯",
              "avoid_crowd": "18点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "环岛路·黄厝海滩",
          "address": "厦门市思明区环岛路",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "最美海滨骑行线，黄厝清晨人少适合看日出。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "黄厝海边",
              "best_time": "清晨",
              "tip": "拍日出与礁石",
              "avoid_crowd": "日出时分",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "沙坡尾·艺术西区",
          "address": "厦门市思明区沙坡尾",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "老避风坞改造的文创港，涂鸦、买手店与咖啡。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "艺术西区门口",
              "best_time": "下午",
              "tip": "拍港景与涂鸦",
              "avoid_crowd": "16点后",
              "day_night": "日",
              "suitable_for": "年轻人"
            }
          ]
        },
        {
          "name": "鹭江夜游",
          "address": "厦门市思明区轮渡码头",
          "time_slot": "evening",
          "duration_min": 90,
          "ticket_price": 80,
          "category": "休闲度假",
          "description": "乘船夜游鼓浪屿海域，看两岸灯光秀。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "船头甲板",
              "best_time": "夜晚",
              "tip": "拍双子塔灯光",
              "avoid_crowd": "20点",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "集美学村",
          "address": "厦门市集美区鳌园路",
          "time_slot": "morning",
          "duration_min": 180,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "嘉庚建筑群与龙舟池，学村红砖琉璃顶极美。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "龙舟池畔",
              "best_time": "上午",
              "tip": "拍对称楼群",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "海沧野生动物园",
          "address": "厦门市海沧区",
          "time_slot": "afternoon",
          "duration_min": 180,
          "ticket_price": 80,
          "category": "亲子",
          "description": "自驾区近距离看散养动物，适合带娃。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "长颈鹿投喂区",
              "best_time": "下午",
              "tip": "拍互动",
              "avoid_crowd": "晴日",
              "day_night": "日",
              "suitable_for": "亲子"
            }
          ]
        }
      ],
      [
        {
          "name": "同安影视城",
          "address": "厦门市同安区",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 40,
          "category": "休闲度假",
          "description": "微缩故宫风格影城，汉服拍照出片。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "天安门微缩",
              "best_time": "上午",
              "tip": "拍红墙金瓦",
              "avoid_crowd": "10点前",
              "day_night": "日",
              "suitable_for": "汉服爱好者"
            }
          ]
        },
        {
          "name": "顶澳仔猫街",
          "address": "厦门市思明区",
          "time_slot": "evening",
          "duration_min": 90,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "厦大旁的猫咪主题街，咖啡与手作小店。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "猫街墙面",
              "best_time": "夜晚",
              "tip": "拍萌系涂鸦",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "年轻人"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "乌糖沙茶面",
        "type": "breakfast",
        "avg_price": 25,
        "specialty": "沙茶面",
        "address": "民族路"
      },
      {
        "name": "小眼镜大排档",
        "type": "lunch",
        "avg_price": 90,
        "specialty": "酱油水海鲜",
        "address": "湖滨中路"
      },
      {
        "name": "临家闽南菜",
        "type": "dinner",
        "avg_price": 120,
        "specialty": "姜母鸭、海蛎煎",
        "address": "多家分店"
      }
    ]
  },
  "长沙": {
    "popular": [
      [
        {
          "name": "橘子洲",
          "address": "长沙市岳麓区橘子洲头",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "湘江中流的绿洲，青年毛泽东雕像与江景大道。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "毛泽东雕像",
              "best_time": "上午",
              "tip": "拍雕像与湘江",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "岳麓山·爱晚亭",
          "address": "长沙市岳麓区登高路",
          "time_slot": "afternoon",
          "duration_min": 160,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "停车坐爱枫林晚，秋天红叶满山，可俯瞰全城。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "爱晚亭",
              "best_time": "下午",
              "tip": "拍红叶古亭",
              "avoid_crowd": "11月",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "岳麓书院",
          "address": "长沙市岳麓区麓山南路",
          "time_slot": "evening",
          "duration_min": 90,
          "ticket_price": 40,
          "category": "人文历史",
          "description": "千年学府，书院夜读氛围安静厚重。",
          "need_booking": true,
          "official_account": "岳麓书院",
          "photo_spots": [
            {
              "position": "书院大门",
              "best_time": "傍晚",
              "tip": "拍古建匾额",
              "avoid_crowd": "17点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "湖南省博物馆",
          "address": "长沙市开福区东风路",
          "time_slot": "morning",
          "duration_min": 180,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "马王堆辛追夫人轰动世界，需提前预约。",
          "need_booking": true,
          "official_account": "湖南博物院",
          "photo_spots": [
            {
              "position": "辛追夫人展厅",
              "best_time": "上午",
              "tip": "拍汉代珍宝",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "太平老街",
          "address": "长沙市天心区太平街",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "贾谊故居旁的老街，糖油粑粑与臭豆腐发源地。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "贾谊故居",
              "best_time": "下午",
              "tip": "拍老街巷",
              "avoid_crowd": "15点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "坡子街·火宫殿",
          "address": "长沙市天心区坡子街",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "长沙美食总汇，火宫殿小吃庙会氛围浓。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "火宫殿戏台",
              "best_time": "夜晚",
              "tip": "拍小吃灯会",
              "avoid_crowd": "18点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "五一广场·IFS",
          "address": "长沙市芙蓉区解放西路",
          "time_slot": "morning",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "城市中心地标，IFS楼顶KAWS雕塑必合影。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "IFS屋顶KAWS",
              "best_time": "上午",
              "tip": "拍雕塑合影",
              "avoid_crowd": "10点前",
              "day_night": "日",
              "suitable_for": "年轻人"
            }
          ]
        },
        {
          "name": "超级文和友",
          "address": "长沙市海信广场",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "复古市井空间，老长沙场景还原，拍照如穿越。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "楼下老街景",
              "best_time": "下午",
              "tip": "拍霓虹老巷",
              "avoid_crowd": "16点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "湘江夜游",
          "address": "长沙市天心区杜甫江阁",
          "time_slot": "evening",
          "duration_min": 90,
          "ticket_price": 60,
          "category": "休闲度假",
          "description": "杜甫江阁登阁看橘子洲焰火（节日），平日夜景也好。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "杜甫江阁",
              "best_time": "夜晚",
              "tip": "拍江阁灯影",
              "avoid_crowd": "20点",
              "day_night": "夜",
              "suitable_for": "摄影爱好者"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "湖南省植物园",
          "address": "长沙市雨花区",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "城市绿肺，春季郁金香与樱花很出片。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "樱花大道",
              "best_time": "上午",
              "tip": "拍花海",
              "avoid_crowd": "3-4月",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "后湖艺术区",
          "address": "长沙市岳麓区",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "湖畔艺术聚落，咖啡、画廊与旧厂房改造。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "湖边步道",
              "best_time": "下午",
              "tip": "拍湖景与涂鸦",
              "avoid_crowd": "晴日",
              "day_night": "日",
              "suitable_for": "年轻人"
            }
          ]
        }
      ],
      [
        {
          "name": "铜官窑古镇",
          "address": "长沙市望城区",
          "time_slot": "morning",
          "duration_min": 200,
          "ticket_price": 100,
          "category": "人文历史",
          "description": "唐代窑址主题古镇，打铁花与机器人博物馆有趣。",
          "need_booking": true,
          "official_account": "铜官窑",
          "photo_spots": [
            {
              "position": "窑街夜景",
              "best_time": "夜晚",
              "tip": "拍打铁花",
              "avoid_crowd": "20点",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "靖港古镇",
          "address": "长沙市望城区",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "湘江畔安静古镇，少商业，适合慢逛。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "古镇码头",
              "best_time": "傍晚",
              "tip": "拍江边落日",
              "avoid_crowd": "17点",
              "day_night": "日",
              "suitable_for": "文艺青年"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "公交新村粉店",
        "type": "breakfast",
        "avg_price": 18,
        "specialty": "长沙米粉",
        "address": "多家分店"
      },
      {
        "name": "费大厨辣椒炒肉",
        "type": "lunch",
        "avg_price": 70,
        "specialty": "辣椒炒肉",
        "address": "多家分店"
      },
      {
        "name": "文和友老长沙龙虾",
        "type": "dinner",
        "avg_price": 140,
        "specialty": "口味虾",
        "address": "海信广场"
      }
    ]
  },
  "南京": {
    "popular": [
      [
        {
          "name": "中山陵",
          "address": "南京市玄武区石象路",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "近代建筑杰作，392级台阶登顶俯瞰紫金山。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "陵门平台",
              "best_time": "上午",
              "tip": "拍蓝瓦白阶",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "明孝陵",
          "address": "南京市玄武区紫金山南",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 70,
          "category": "人文历史",
          "description": "明代皇陵，石象路神道秋色绝美。",
          "need_booking": true,
          "official_account": "明孝陵",
          "photo_spots": [
            {
              "position": "石象路",
              "best_time": "下午",
              "tip": "拍神道石兽",
              "avoid_crowd": "11月",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "夫子庙·秦淮河",
          "address": "南京市秦淮区贡院街",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "桨声灯影秦淮河，小吃与画舫夜游。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "文德桥",
              "best_time": "夜晚",
              "tip": "拍河中灯影",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "南京博物院",
          "address": "南京市玄武区中山东路321号",
          "time_slot": "morning",
          "duration_min": 180,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "仅次于故宫的博物院，民国馆可拍照穿越。",
          "need_booking": true,
          "official_account": "南京博物院",
          "photo_spots": [
            {
              "position": "民国馆街道",
              "best_time": "上午",
              "tip": "拍复古街景",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "总统府",
          "address": "南京市玄武区长江路292号",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 35,
          "category": "人文历史",
          "description": "近代政治中枢，江南园林与西式建筑并存。",
          "need_booking": true,
          "official_account": "南京总统府",
          "photo_spots": [
            {
              "position": "煦园",
              "best_time": "下午",
              "tip": "拍园林水榭",
              "avoid_crowd": "14点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "老门东",
          "address": "南京市秦淮区箍桶巷",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "比夫子庙更文艺的老城南，蒋有记锅贴与手作店。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "芥子园",
              "best_time": "夜晚",
              "tip": "拍巷灯",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "鸡鸣寺",
          "address": "南京市玄武区鸡鸣寺路",
          "time_slot": "morning",
          "duration_min": 120,
          "ticket_price": 10,
          "category": "人文历史",
          "description": "南朝名刹，樱花季如雪，可顺登明城墙。",
          "need_booking": true,
          "official_account": "鸡鸣寺",
          "photo_spots": [
            {
              "position": "寺前樱花道",
              "best_time": "上午",
              "tip": "拍古寺樱花",
              "avoid_crowd": "3月",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "玄武湖",
          "address": "南京市玄武区玄武巷",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "城中湖，环湖步道与情侣园，可划船。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "玄武门城头",
              "best_time": "傍晚",
              "tip": "拍湖天一色",
              "avoid_crowd": "17点",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "新街口",
          "address": "南京市秦淮区新街口",
          "time_slot": "evening",
          "duration_min": 90,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "中华第一商圈，德基广场与地下连廊极繁华。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "德基广场",
              "best_time": "夜晚",
              "tip": "拍商场光影",
              "avoid_crowd": "20点",
              "day_night": "夜",
              "suitable_for": "年轻人"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "先锋书店(五台山)",
          "address": "南京市鼓楼区广州路",
          "time_slot": "morning",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "防空洞改造的人文书店，十字架长廊是打卡点。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "十字走廊",
              "best_time": "上午",
              "tip": "拍书店光影",
              "avoid_crowd": "工作日上午",
              "day_night": "日",
              "suitable_for": "文艺青年"
            }
          ]
        },
        {
          "name": "颐和路公馆区",
          "address": "南京市鼓楼区颐和路",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "民国公馆建筑群，梧桐掩映的安静街区。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "颐和路梧桐",
              "best_time": "下午",
              "tip": "拍民国老宅",
              "avoid_crowd": "晴日",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        }
      ],
      [
        {
          "name": "牛首山",
          "address": "南京市江宁区宁丹大道",
          "time_slot": "morning",
          "duration_min": 200,
          "ticket_price": 98,
          "category": "人文历史",
          "description": "佛顶宫地宫震撼，舍利供奉处建筑奇绝。",
          "need_booking": true,
          "official_account": "牛首山",
          "photo_spots": [
            {
              "position": "佛顶宫穹顶",
              "best_time": "上午",
              "tip": "拍金顶穹宇",
              "avoid_crowd": "开园即入",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "桦墅村",
          "address": "南京市栖霞区",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "近郊文艺村落，稻田与咖啡馆，适合周末放空。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "村口稻田",
              "best_time": "傍晚",
              "tip": "拍田园落日",
              "avoid_crowd": "17点",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "鸡鸣汤包",
        "type": "breakfast",
        "avg_price": 20,
        "specialty": "汤包、鸭血粉丝",
        "address": "多家分店"
      },
      {
        "name": "南京大牌档",
        "type": "lunch",
        "avg_price": 80,
        "specialty": "盐水鸭、美龄粥",
        "address": "多家分店"
      },
      {
        "name": "狮子桥美食街",
        "type": "dinner",
        "avg_price": 100,
        "specialty": "活珠子、梅花糕",
        "address": "湖南路"
      }
    ]
  },
  "上海": {
    "popular": [
      [
        {
          "name": "外滩",
          "address": "上海市黄浦区中山东一路",
          "time_slot": "morning",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "万国建筑群与陆家嘴天际线隔江对望，清晨人少。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "外白渡桥",
              "best_time": "清晨",
              "tip": "拍桥与晨光",
              "avoid_crowd": "7点前",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            },
            {
              "position": "观景平台",
              "best_time": "夜晚",
              "tip": "拍陆家嘴灯光",
              "avoid_crowd": "20点",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "南京路步行街",
          "address": "上海市黄浦区南京东路",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "美食",
          "description": "中华商业第一街，老字号食品与霓虹橱窗。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "世纪广场",
              "best_time": "下午",
              "tip": "拍霓虹街景",
              "avoid_crowd": "16点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "豫园·城隍庙",
          "address": "上海市黄浦区安仁街",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 40,
          "category": "人文历史",
          "description": "明代园林与老城厢小吃，南翔小笼发源地。",
          "need_booking": true,
          "official_account": "豫园",
          "photo_spots": [
            {
              "position": "九曲桥",
              "best_time": "夜晚",
              "tip": "拍园林灯影",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ],
      [
        {
          "name": "东方明珠·陆家嘴",
          "address": "上海市浦东新区世纪大道1号",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 160,
          "category": "网红打卡",
          "description": "登塔看三件套与黄浦江，透明观光廊刺激。",
          "need_booking": true,
          "official_account": "东方明珠",
          "photo_spots": [
            {
              "position": "城市观景台",
              "best_time": "上午",
              "tip": "拍江景天际线",
              "avoid_crowd": "10点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "上海博物馆",
          "address": "上海市黄浦区人民大道201号",
          "time_slot": "afternoon",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "青铜与书画顶级收藏，需预约。",
          "need_booking": true,
          "official_account": "上海博物馆",
          "photo_spots": [
            {
              "position": "中央大厅",
              "best_time": "下午",
              "tip": "拍建筑中庭",
              "avoid_crowd": "14点后",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "新天地",
          "address": "上海市黄浦区太仓路",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "石库门改造的时尚街区，酒吧与精致餐饮。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "石库门弄堂",
              "best_time": "夜晚",
              "tip": "拍中西合璧建筑",
              "avoid_crowd": "19点后",
              "day_night": "夜",
              "suitable_for": "年轻人"
            }
          ]
        }
      ],
      [
        {
          "name": "武康路·衡复风貌区",
          "address": "上海市徐汇区武康路",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "梧桐掩映的百年马路，武康大楼是地标。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "武康大楼",
              "best_time": "上午",
              "tip": "拍三角大楼",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "思南公馆",
          "address": "上海市黄浦区思南路",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "花园洋房群与独立书店，安静文艺。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "思南文学之家",
              "best_time": "下午",
              "tip": "拍洋房庭院",
              "avoid_crowd": "15点后",
              "day_night": "日",
              "suitable_for": "文艺青年"
            }
          ]
        },
        {
          "name": "北外滩滨江",
          "address": "上海市虹口区滨江",
          "time_slot": "evening",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "看陆家嘴最佳新机位，人比外滩少。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "滨江观景台",
              "best_time": "夜晚",
              "tip": "拍三件套倒影",
              "avoid_crowd": "20点",
              "day_night": "夜",
              "suitable_for": "所有人"
            }
          ]
        }
      ]
    ],
    "niche": [
      [
        {
          "name": "田子坊",
          "address": "上海市黄浦区泰康路",
          "time_slot": "morning",
          "duration_min": 130,
          "ticket_price": 0,
          "category": "网红打卡",
          "description": "石库门里弄改造的创意市集，巷弄迷宫有趣。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "弄堂入口",
              "best_time": "上午",
              "tip": "拍里弄烟火",
              "avoid_crowd": "10点前",
              "day_night": "日",
              "suitable_for": "所有人"
            }
          ]
        },
        {
          "name": "多伦路文化街",
          "address": "上海市虹口区多伦路",
          "time_slot": "afternoon",
          "duration_min": 110,
          "ticket_price": 0,
          "category": "人文历史",
          "description": "鲁迅、茅盾旧居云集，老派文化街。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "名人雕塑墙",
              "best_time": "下午",
              "tip": "拍老街铜像",
              "avoid_crowd": "晴日",
              "day_night": "日",
              "suitable_for": "文艺青年"
            }
          ]
        }
      ],
      [
        {
          "name": "杨浦滨江·绿之丘",
          "address": "上海市杨浦区杨树浦路",
          "time_slot": "morning",
          "duration_min": 150,
          "ticket_price": 0,
          "category": "自然风光",
          "description": "工业遗存改造的滨江步道，绿之丘如空中花园。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "绿之丘露台",
              "best_time": "上午",
              "tip": "拍江景与钢架",
              "avoid_crowd": "9点前",
              "day_night": "日",
              "suitable_for": "摄影爱好者"
            }
          ]
        },
        {
          "name": "安福路",
          "address": "上海市徐汇区安福路",
          "time_slot": "afternoon",
          "duration_min": 120,
          "ticket_price": 0,
          "category": "休闲度假",
          "description": "话剧中心与小众买手店，上海时髦精聚集地。",
          "need_booking": false,
          "official_account": "",
          "photo_spots": [
            {
              "position": "话剧艺术中心",
              "best_time": "下午",
              "tip": "拍街角咖啡",
              "avoid_crowd": "16点后",
              "day_night": "日",
              "suitable_for": "年轻人"
            }
          ]
        }
      ]
    ],
    "meals": [
      {
        "name": "南翔馒头店",
        "type": "breakfast",
        "avg_price": 35,
        "specialty": "蟹粉小笼",
        "address": "豫园老街"
      },
      {
        "name": "老正兴菜馆",
        "type": "lunch",
        "avg_price": 110,
        "specialty": "油爆河虾、草头圈子",
        "address": "福州路"
      },
      {
        "name": "人和馆",
        "type": "dinner",
        "avg_price": 130,
        "specialty": "本帮红烧肉、熏鱼",
        "address": "多家分店"
      }
    ]
  }
};

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
  const slotOrder = { morning: 0, afternoon: 1, evening: 2 }
  const slotStart = { morning: 540, afternoon: 840, evening: 1110 } // 09:00 / 14:00 / 18:30
  const mealTime = { breakfast: 480, lunch: 750, dinner: 1140 } // 08:00 / 12:30 / 19:00
  const pad = (n) => (n < 10 ? '0' + n : '' + n)
  const toHHMM = (m) => pad(Math.floor(m / 60)) + ':' + pad(m % 60)
  // 按类型分组餐饮，便于每天轮换选取两类
  const mealsByType = { breakfast: [], lunch: [], dinner: [] }
  meals.forEach(m => { (mealsByType[m.type] || (mealsByType[m.type] = [])).push(m) })

  for (let i = 1; i <= days; i++) {
    const plan = dayPlans[(i - 1) % dayPlans.length]
    const rawSpots = (repo ? plan : fill(plan, city))
    // 按上午/下午/晚上排序，并为每个景点安排精确开始时间
    const sorted = rawSpots.slice().sort((a, b) => (slotOrder[a.time_slot] || 0) - (slotOrder[b.time_slot] || 0))
    const slotNext = Object.assign({}, slotStart)
    const spots = sorted.map(attachImage).map(s => {
      const slot = s.time_slot || 'morning'
      const start = slotNext[slot]
      s.start_time = toHHMM(start)
      slotNext[slot] = start + (s.duration_min || 120) + 30
      s.best_price = s.ticket_price
      if (s.ticket_price > 0) s.ticket_channel = s.official_account ? '景区官方' : pick(ticketCh, s.name)
      return s
    })
    // 当天餐饮：轮换两类（午/晚/早），保证不重样且带时间
    const types = ['lunch', 'dinner', 'breakfast']
    const t1 = types[(i - 1) % 3]
    const t2 = types[i % 3]
    const dayMeals = [t1, t2].map(t => {
      const arr = mealsByType[t] || []
      if (!arr.length) return null
      const m = arr[(i - 1) % arr.length]
      const mm = Object.assign({}, m)
      mm.start_time = toHHMM(mealTime[t] || 750)
      mm.deal_channel = pick(dealCh, m.name)
      return mm
    }).filter(Boolean)

    // 生成节点间交通（酒店 → 各景点/餐饮，按时间排序 → 回酒店）
    const nodes = spots.map(s => ({ name: s.name, time: s.start_time }))
      .concat(dayMeals.map(m => ({ name: m.name, time: m.start_time })))
      .sort((a, b) => a.time.localeCompare(b.time))
    const transport = []
    let prev = '酒店'
    nodes.forEach(n => {
      if (n.name !== prev) {
        transport.push({ from: prev, to: n.name, mode: p.transport_mode || '地铁', duration_min: 30, cost: 5 })
        prev = n.name
      }
    })
    if (nodes.length) transport.push({ from: prev, to: '酒店', mode: p.transport_mode || '地铁', duration_min: 30, cost: 5 })

    const budget = Math.max(100, perDayAvg + (i % 3 - 1) * 30)
    total += budget
    itinerary.push({
      day_number: i,
      date_label: ['一', '二', '三', '四'][i - 1] ? `第${['一', '二', '三', '四'][i - 1]}天` : `第${i}天`,
      spots,
      meals: dayMeals,
      transport,
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
  const deletedMockIds = wx.getStorageSync('deletedMockTripIds') || []
  const visibleMockTrips = MOCK_TRIPS.filter(t => !deletedMockIds.includes(t.id))
  if (url.includes('/auth/login')) {
    return { code: 0, data: { token: 'mock-token-' + Date.now(), user: mockUser }, message: 'ok' }
  }
  if (url.includes('/user/info') || url.includes('/user/me')) {
    return { code: 0, data: mockUser, message: 'ok' }
  }
  if (url.includes('/user/stats')) {
    const local = wx.getStorageSync('localTrips') || []
    return { code: 0, data: { tripCount: visibleMockTrips.length + local.length, cityCount: 6 }, message: 'ok' }
  }
  if (url.includes('/user/points')) {
    return { code: 0, data: { points: mockUser.points }, message: 'ok' }
  }
  if (url.includes('/user/recharge')) {
    return { code: 0, data: { message: '充值申请已提交，请扫码支付后联系客服加积分' }, message: 'ok' }
  }
  if (url.includes('/trip/list')) {
    const status = data.status
    let list = visibleMockTrips
    if (status === 'active') list = list.filter(t => t.status === 'active')
    // 合并本地保存的行程
    const local = wx.getStorageSync('localTrips') || []
    list = list.concat(local)
    return { code: 0, data: { list }, message: 'ok' }
  }
  if (url.includes('/trip/detail')) {
    const all = visibleMockTrips.concat(wx.getStorageSync('localTrips') || [])
    const t = all.find(x => x.id === data.id)
    return { code: 0, data: { trip: t || visibleMockTrips[0] || MOCK_TRIPS[0] }, message: 'ok' }
  }
  if (url.includes('/trip/save')) {
    const local = wx.getStorageSync('localTrips') || []
    const trip = { ...data.trip, id: 'loc' + Date.now(), created_at: Date.now(), status: 'active' }
    local.unshift(trip)
    wx.setStorageSync('localTrips', local)
    return { code: 0, data: { id: trip.id }, message: 'ok' }
  }
  if (url.includes('/trip/delete')) {
    const sid = String(data.id || '')
    if (sid.startsWith('t')) {
      // 预置示例行程：记录到删除列表，下次 list/detail 过滤掉
      const ids = wx.getStorageSync('deletedMockTripIds') || []
      if (!ids.includes(data.id)) {
        ids.push(data.id)
        wx.setStorageSync('deletedMockTripIds', ids)
      }
    } else {
      let local = wx.getStorageSync('localTrips') || []
      local = local.filter(t => t.id !== data.id)
      wx.setStorageSync('localTrips', local)
    }
    return { code: 0, data: {}, message: 'ok' }
  }
  if (url.includes('/plan/form') || url.includes('/plan/quick')) {
    // 个人主体（MONETIZATION_ENABLED=false）：不扣积分、不拦截，AI 生成免费可用
    if (monetizationEnabled && mockUser.points < 10) {
      return { code: 4001, data: null, message: '积分不足，请充值后再生成行程' }
    }
    if (monetizationEnabled) mockUser.points -= 10
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
    // 个人主体：不扣积分、不拦截，AI 问答免费可用
    if (monetizationEnabled && mockUser.points < 2) {
      return { code: 4001, data: null, message: '积分不足，请充值后再提问' }
    }
    if (monetizationEnabled) mockUser.points -= 2
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

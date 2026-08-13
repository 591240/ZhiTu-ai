import json
import logging
import re

from app.ai.llm_client import llm_client
from app.config import settings
from app.services import image_service

logger = logging.getLogger(__name__)

# ===== 景点库（Mock 生成器使用，无 LLM Key 时返回示例行程） =====
SPOTS = {
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": True,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": True,
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
                    "need_booking": True,
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
                    "need_booking": True,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
                    "need_booking": False,
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
}

GENERIC = {
    "popular": [
        [
            {"name": "{city}博物馆", "address": "{city}市中心", "time_slot": "morning", "duration_min": 150, "ticket_price": 0, "category": "人文历史", "description": "了解城市历史的好去处。"},
            {"name": "{city}中央公园", "address": "{city}新区", "time_slot": "afternoon", "duration_min": 140, "ticket_price": 0, "category": "自然风光", "description": "城市绿肺，适合散步。"},
        ],
        [
            {"name": "{city}老街", "address": "{city}老城区", "time_slot": "evening", "duration_min": 120, "ticket_price": 0, "category": "美食", "description": "本地小吃与夜市。"},
        ],
    ],
    "niche": [
        [
            {"name": "{city}近郊徒步线", "address": "{city}郊外", "time_slot": "morning", "duration_min": 200, "ticket_price": 0, "category": "自然风光", "description": "避开人流的秘境路线。"},
        ],
        [
            {"name": "{city}独立书店", "address": "{city}文艺街区", "time_slot": "afternoon", "duration_min": 120, "ticket_price": 0, "category": "休闲度假", "description": "城市文化角落。"},
        ],
    ],
    "meals": [
        {"name": "{city}特色菜馆", "type": "lunch", "avg_price": 80, "specialty": "本地招牌菜", "address": "市中心"},
        {"name": "{city}夜市", "type": "dinner", "avg_price": 60, "specialty": "街头小吃", "address": "老城区"},
    ],
}


def _fill(tpl, city):
    return _fill_obj(tpl, city)


def _fill_obj(obj, city):
    if isinstance(obj, str):
        return obj.replace("{city}", city)
    if isinstance(obj, list):
        return [_fill_obj(x, city) for x in obj]
    if isinstance(obj, dict):
        return {k: _fill_obj(v, city) for k, v in obj.items()}
    return obj


def gen_trip(p: dict) -> dict:
    city = p.get("city") or "杭州"
    days = max(1, min(int(p.get("days") or 2), 4))
    route_type = "niche" if p.get("route_type") == "niche" else "popular"
    repo = SPOTS.get(city)
    base = repo if repo else GENERIC
    day_plans = base["niche"] if route_type == "niche" else base["popular"]
    meals = base["meals"]

    budget_min = int(p.get("budget_min") or 500)
    budget_max = int(p.get("budget_max") or 1500)
    if budget_max < budget_min:
        budget_max = budget_min
    per_day_avg = (budget_min + budget_max) // 2 // days

    itinerary = []
    total = 0
    slot_order = {"morning": 0, "afternoon": 1, "evening": 2}
    slot_start = {"morning": 540, "afternoon": 840, "evening": 1110}
    meal_time = {"breakfast": 480, "lunch": 750, "dinner": 1140}

    def to_hhmm(m):
        return f"{m // 60:02d}:{m % 60:02d}"

    meals_by_type = {"breakfast": [], "lunch": [], "dinner": []}
    for _m in meals:
        meals_by_type.setdefault(_m.get("type"), []).append(_m)

    for i in range(1, days + 1):
        plan = day_plans[(i - 1) % len(day_plans)]
        raw = plan if repo else _fill_obj(plan, city)
        raw = [dict(s) for s in raw]
        raw.sort(key=lambda s: slot_order.get(s.get("time_slot"), 0))
        slot_next = dict(slot_start)
        spots = []
        for s in raw:
            _fill_photo(s)
            s["image"] = image_service.get_spot_image(s.get("name", ""), city) or ""
            slot = s.get("time_slot", "morning")
            start = slot_next[slot]
            s["start_time"] = to_hhmm(start)
            slot_next[slot] = start + int(s.get("duration_min", 120)) + 30
            s.setdefault("best_price", s.get("ticket_price", 0))
            if s.get("ticket_price", 0) > 0:
                s["ticket_channel"] = "景区官方" if s.get("official_account") else "美团"
            spots.append(s)
        types = ["lunch", "dinner", "breakfast"]
        t1 = types[(i - 1) % 3]
        t2 = types[i % 3]
        day_meals = []
        for _t in (t1, t2):
            _arr = meals_by_type.get(_t) or []
            if not _arr:
                continue
            _mm = dict(_arr[(i - 1) % len(_arr)])
            _mm["start_time"] = to_hhmm(meal_time.get(_t, 750))
            _mm.setdefault("deal_channel", "美团")
            day_meals.append(_mm)
        nodes = [{"name": s["name"], "time": s["start_time"]} for s in spots]
        nodes += [{"name": _m["name"], "time": _m["start_time"]} for _m in day_meals]
        nodes.sort(key=lambda n: n["time"])
        transport = []
        prev = "酒店"
        for _n in nodes:
            if _n["name"] != prev:
                transport.append({"from": prev, "to": _n["name"], "mode": p.get("transport_mode") or "地铁", "duration_min": 30, "cost": 5})
                prev = _n["name"]
        if nodes:
            transport.append({"from": prev, "to": "酒店", "mode": p.get("transport_mode") or "地铁", "duration_min": 30, "cost": 5})
        budget = max(100, per_day_avg + (i % 3 - 1) * 30)
        total += budget
        itinerary.append({
            "day_number": i,
            "date_label": f"第{i}天",
            "weather_tip": "建议出行前关注当地天气预报，备好相应装备",
            "season_tip": "热门景点建议错峰，早到可避开人流",
            "crowd_tip": "优先选择开园/开门首时段游览",
            "spots": spots,
            "meals": day_meals,
            "transport": transport,
            "budget": budget,
            "tips": "• 出行前查看天气，备好舒适鞋\n• 热门景点建议错峰前往" if i == 1 else "• 注意保管随身物品\n• 用餐可参考本地人排队店铺",
        })

    title = f"{city}{days}日{'小众深度' if route_type == 'niche' else '经典大众'}游"
    return {
        "title": title,
        "city": city,
        "days": days,
        "route_type": route_type,
        "crowd_type": p.get("crowd_type") or "朋友",
        "budget_min": budget_min,
        "budget_max": budget_max,
        "budget_level": "经济" if budget_max < 500 else "高端" if budget_max > 1500 else "舒适",
        "content": {
            "itinerary": itinerary,
            "total_budget": total,
            "transport_plans": [],
            "budget_analysis": f"预估人均总花费约 ¥{total}，按您设置的 ¥{budget_min}-¥{budget_max}/人预算规划，含景点门票、餐饮与市内交通，仅供参考。",
            "preparations": cross_border_preparations(city),
        },
    }


# 跨境/特殊地区行前准备示例（港澳通行证、签证、电话卡等）
def cross_border_preparations(city: str) -> list:
    c = (city or "").replace("{city}", "").strip()
    if "香港" in c:
        return [
            {"icon": "🛂", "title": "办理港澳通行证及签注", "detail": "需持有效港澳通行证并办理赴港签注（个人游G签或团队游L签），建议提前10个工作日办理。"},
            {"icon": "📱", "title": "电话卡 / 漫游", "detail": "提前开通港澳台漫游或购买香港本地电话卡，确保地图、打车、导航可用。"},
            {"icon": "💳", "title": "货币与支付", "detail": "香港使用港币，八达通/支付宝香港/微信香港钱包通用，建议备少量现金。"},
            {"icon": "🔌", "title": "转换插头", "detail": "英标插头（三方脚），电压220V，出行前备好转换头。"},
        ]
    if "澳门" in c:
        return [
            {"icon": "🛂", "title": "办理港澳通行证及签注", "detail": "需持有效港澳通行证并办理赴澳签注，建议提前10个工作日办理。"},
            {"icon": "📱", "title": "电话卡 / 漫游", "detail": "提前开通港澳台漫游或购买澳门本地电话卡。"},
            {"icon": "💳", "title": "货币与支付", "detail": "澳门使用澳门元/港币，多数商户支持支付宝微信，建议备少量现金。"},
            {"icon": "🔌", "title": "转换插头", "detail": "英标插头，电压220V，备好转换头。"},
        ]
    if "台湾" in c:
        return [
            {"icon": "🛂", "title": "办理入台证", "detail": "需大通证+入台证（通过有资质的旅行社办理），提前2-3周准备。"},
            {"icon": "📱", "title": "电话卡 / 漫游", "detail": "开通港澳台漫游或购买台湾本地电话卡。"},
            {"icon": "💳", "title": "货币与支付", "detail": "台湾使用新台币，街口/Line Pay常用，备少量现金。"},
            {"icon": "🔌", "title": "转换插头", "detail": "美标插头，电压110V，需转换头+变压器。"},
        ]
    return []


def _fill_photo(spot: dict) -> dict:
    s = dict(spot)
    s.setdefault("photo_spots", [{
        "position": "景区标志性观景点",
        "best_time": "上午或日落",
        "tip": "利用自然光拍出通透感",
        "avoid_crowd": "开园首小时抵达",
        "day_night": "日",
        "suitable_for": "所有人",
    }])
    return s


SCHEMA_HINT = """你是专业旅游行程规划师。严格只输出如下 JSON 结构（不要任何多余文字或解释）：
{
  "title":"行程标题",
  "city":"城市",
  "days":2,
  "route_type":"popular 或 niche",
  "crowd_type":"人群类型",
  "budget_min":500,
  "budget_max":1500,
  "content":{
    "transport_plans":[
      {"name":"省时方案","mode":"高铁/飞机/自驾/大巴","price":1200,"duration":"约3小时","pros":"最快到达","cons":"价格较高","arrival_note":"抵达后建议先到酒店寄存行李再游玩"}
    ],
    "itinerary":[
      {
        "day_number":1,
        "date_label":"第1天",
        "weather_tip":"今日晴，注意防晒补水（若未知天气则给通用建议）",
        "season_tip":"当前为旺季/淡季，热门景点人多，建议错峰",
        "crowd_tip":"建议上午9点前到达避开人流高峰",
        "spots":[
          {"name":"景点名","address":"地址","time_slot":"morning/afternoon/evening","duration_min":120,"ticket_price":0,"best_price":0,"ticket_channel":"景区官方/携程/美团/抖音团购（AI预估最划算购票渠道）","need_booking":False,"official_account":"","category":"自然风光/人文历史/美食/网红打卡/休闲度假","description":"一句话简介","photo_spots":[{"position":"观景台东侧","best_time":"日出/日落/上午/下午/夜晚","tip":"低角度拍湖面反光更有层次","avoid_crowd":"开园前30分钟抵达","day_night":"日/夜","suitable_for":"摄影爱好者/家庭/情侣"}]}
        ],
        "meals":[{"name":"餐厅名","type":"lunch/dinner/breakfast","avg_price":80,"deal_channel":"美团/大众点评/抖音团购（AI预估最划算团购渠道）","specialty":"招牌菜","address":"地址"}],
        "transport":[{"from":"酒店","to":"景点","mode":"地铁/公交/步行/打车","duration_min":30,"cost":5}],
        "budget":500,
        "tips":"当日实用提示"
      }
    ],
    "total_budget":1500,
    "budget_analysis":"总预算构成说明：门票约X元、餐饮约Y元、市内交通约Z元、人均约W元，并说明省钱/升级建议",
    "preparations":[
      {"icon":"🛂","title":"办理港澳通行证及签注","detail":"前往香港/澳门需持有效港澳通行证并办理赴港/澳签注（个人游G签或团队游L签），建议提前10个工作日办理"},
      {"icon":"📱","title":"电话卡 / 漫游","detail":"提前开通港澳台漫游或购买当地电话卡，确保导航、打车、地图可用"}
    ]
  }
}
价格与渠道规则：门票/餐饮请基于常识给出 AI 预估最优价（景点用 ticket_price/best_price，餐饮用 avg_price），并为每个收费景点与每餐推荐一个最划算的购买/团购渠道——景点填 ticket_channel、餐饮填 deal_channel，取值从 {景区官方, 携程, 美团, 飞猪, 同程, 抖音团购, 大众点评} 中选最划算的一个；前端将据此展示「AI 推荐 ¥X · 去XX购买」并一键跳转比价/购买。价格仅为 AI 预估，实际以下单页为准。
要求：transport_plans 必须恰好给出 3 套方案，分别命名为「省时方案」「性价比方案」「舒适方案」，覆盖往返大交通；每个景点至少给出 1 个 photo_spots 打卡机位；weather_tip/season_tip/crowd_tip 每日均需填写。
重要约束：itinerary 里的每个 spot 必须是真实可游览的景点或体验（景区、街区、博物馆、自然风光、市集、演出等），严禁把火车站/高铁站/机场/地铁站/汽车站/码头/仅用于住宿的酒店等交通站点或住宿设施当作景点写入 spots；往返与市内交通一律放进 transport 字段（由系统按时间轴自动串接），不要把「前往车站」「入住酒店」列为景点。每天建议安排 2-3 个景点 + 1-2 餐，并为每个 spot 标注 start_time（HH:MM，如 09:00）与精确时长 duration_min，便于前端渲染当日时间轴。
行前准备规则（务必遵守）：若目的地为港澳台或出境（如香港、澳门、国外城市），必须在 content.preparations 中列出该目的地行前必办事项，至少覆盖：①证件（护照/签证、港澳通行证及签注）；②电话卡或国际漫游；③货币与移动支付的跨境使用；④转换插头/电压；⑤海关与防疫注意事项。每项含 icon（emoji）、title、detail 三个字段，detail 为可操作的具体提醒。若目的地为国内大陆城市，preparations 返回空数组 []。"""


def _season_crowd_hint(p: dict) -> str:
    """基于出发日期（按月+节假日）推算季节/客流适配规则，零 API 成本。"""
    import datetime as _dt
    today = _dt.date.today()
    sd = (p or {}).get("start_date") or ""
    try:
        d = _dt.datetime.strptime(sd, "%Y-%m-%d").date()
    except Exception:
        d = today
    month = d.month
    if month in (12, 1, 2):
        season = "冬季"
    elif month in (3, 4, 5):
        season = "春季"
    elif month in (6, 7, 8):
        season = "夏季"
    else:
        season = "秋季"
    peak = (month in (7, 8)
            or (month == 10 and 1 <= d.day <= 7)
            or (month == 5 and 1 <= d.day <= 5)
            or (month == 1 and 25 <= d.day <= 31)
            or (month == 2 and d.day <= 15))
    peak_label = "旺季（人多价高）" if peak else "淡季/平季（人流较少）"
    is_weekend = d.weekday() >= 5
    crowd = "周末出行，热门景点人流偏大" if is_weekend else "工作日出行，相对宽松"
    rules = (
        "环境适配硬规则（务必在输出中体现）："
        "①若为雨天方案优先安排室内景点；"
        "②夏季高温日将户外景点安排在上午或傍晚，避开10:00-16:00；"
        "③大风/恶劣天气取消登山、游船等高危项目；"
        "④旺季主动推荐错峰时段与小众机位，减少排队。"
    )
    return f"环境背景：出发月份推算为{season}、{peak_label}、{crowd}。\n{rules}"


class PlanService:
    async def generate_from_form(self, req) -> dict:
        if settings.llm_api_key:
            try:
                data = await llm_client.generate_json(self._form_prompt(req.dict()))
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    return self._normalize(data, req.dict())
                logger.warning("LLM 返回结构异常，回退示例生成：%s", data)
            except Exception:
                logger.exception("LLM 调用失败，回退示例生成")
        return gen_trip(req.dict())

    async def generate_from_quick(self, text: str) -> dict:
        if settings.llm_api_key:
            try:
                data = await llm_client.generate_json(self._quick_prompt(text))
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    return self._normalize(data, {"city": "杭州", "days": 2})
                logger.warning("LLM 返回结构异常，回退示例生成：%s", data)
            except Exception:
                logger.exception("LLM 调用失败，回退示例生成")
        city = "杭州"
        for c in SPOTS.keys():
            if c in text:
                city = c
                break
        m = re.search(r"(\d+)\s*天", text)
        days = int(m.group(1)) if m else 2
        route_type = "niche" if any(w in text for w in ["小众", "深度", "冷门"]) else "popular"
        return gen_trip({"city": city, "days": days, "route_type": route_type, "transport_mode": "地铁"})

    def _form_prompt(self, p):
        prefs = ",".join(p.get("preferences") or [])
        env_hint = _season_crowd_hint(p)
        return SCHEMA_HINT + (
            f"\n参数：目的地={p.get('city')}，出发地={p.get('departure_city') or '未指定'}，"
            f"天数={p.get('days')}，人群={p.get('crowd_type')}，人数={p.get('people_count') or 2}人，"
            f"预算范围={p.get('budget_min', 0)}-{p.get('budget_max', 0)}元/人，偏好={prefs}，市内交通={p.get('transport_mode')}，"
            f"往返偏好={p.get('transport_preference') or '未指定'}，"
            f"出发日期={p.get('start_date') or '未指定'}，返程日期={p.get('end_date') or '未指定'}，"
            f"路线={p.get('route_type')}，备注={p.get('remark', '')}。"
            f"\n{env_hint}\n只输出JSON。"
        )

    def _quick_prompt(self, text):
        env_hint = _season_crowd_hint({})
        return SCHEMA_HINT + f"\n用户需求：{text}。{env_hint}\n只输出JSON。"

    def _normalize(self, data, p):
        data.setdefault("title", f"{p.get('city', '')}行程")
        data.setdefault("city", p.get("city", "杭州"))
        data.setdefault("days", p.get("days", 2))
        data.setdefault("route_type", p.get("route_type", "popular"))
        data.setdefault("crowd_type", p.get("crowd_type", "朋友"))
        data.setdefault("budget_min", p.get("budget_min", 500))
        data.setdefault("budget_max", p.get("budget_max", 1500))
        # 兼容旧字段与前端展示：根据预算范围自动映射档位标签
        _max = data.get("budget_max") or 1500
        data.setdefault("budget_level", "经济" if _max < 500 else "高端" if _max > 1500 else "舒适")
        content = data.setdefault("content", {})
        content.setdefault("itinerary", [])
        content.setdefault("total_budget", 0)
        content.setdefault("transport_plans", [])
        content.setdefault("budget_analysis", "")
        content.setdefault("preparations", [])
        trip_city = data.get("city", "")
        for day in content["itinerary"]:
            day.setdefault("weather_tip", "")
            day.setdefault("season_tip", "")
            day.setdefault("crowd_tip", "")
            day.setdefault("spots", [])
            day.setdefault("meals", [])
            day.setdefault("transport", [])
            day.setdefault("budget", 0)
            day.setdefault("tips", "")
            for spot in day["spots"]:
                spot.setdefault("photo_spots", [])
                spot.setdefault("duration_min", 120)
                spot.setdefault("ticket_price", 0)
                spot.setdefault("best_price", spot.get("ticket_price", 0))
                spot.setdefault("ticket_channel", "")
                spot.setdefault("need_booking", False)
                spot.setdefault("official_account", "")
                spot.setdefault("description", "")
                spot.setdefault("category", "")
                spot.setdefault("address", "")
                if not spot.get("image"):
                    spot["image"] = image_service.get_spot_image(spot.get("name", ""), trip_city) or ""
                for ps in spot["photo_spots"]:
                    ps.setdefault("position", "")
                    ps.setdefault("best_time", "")
                    ps.setdefault("tip", "")
                    ps.setdefault("avoid_crowd", "")
                    ps.setdefault("day_night", "")
                    ps.setdefault("suitable_for", "")
            for meal in day["meals"]:
                meal.setdefault("deal_channel", "")
                meal.setdefault("avg_price", 0)
                meal.setdefault("specialty", "")
                meal.setdefault("address", "")
                meal.setdefault("type", "lunch")
        return data

    async def adjust(self, trip: dict, instruction: str):
        """对话微调：携带当前行程上下文，调用 LLM 真正理解并执行修改指令。

        返回 (reply, new_trip)。无 LLM Key 或解析失败时优雅降级（返回原行程 + 提示）。
        """
        trip = trip or {}
        tid = trip.get("id")
        if settings.llm_api_key:
            try:
                data = await llm_client.generate_json(self._adjust_prompt(trip, instruction))
                # LLM 返回 { reply, title, city, days, ..., content }
                if data and isinstance(data, dict) and data.get("content", {}).get("itinerary"):
                    reply = data.pop("reply", "已为你调整行程。")
                    new_trip = self._normalize_adjust(data)
                    if tid is not None:
                        new_trip["id"] = tid
                    return reply, new_trip
                logger.warning("LLM 微调返回结构异常，回退原行程：%s", data)
            except Exception:
                logger.exception("LLM 微调调用失败，回退原行程")

        # 降级：诚实提示，不伪造修改（保留原 id 以便前端仍可保存）
        if tid is not None:
            trip = dict(trip)
            trip["id"] = tid
        return (
            "（当前为离线演示模式，未接入大模型，暂无法智能微调行程。"
            "请在服务端配置 LLM_API_KEY 后重试。）",
            trip,
        )

    def _adjust_prompt(self, trip: dict, instruction: str) -> str:
        trip_json = json.dumps(trip, ensure_ascii=False)
        return (
            "你是旅游行程微调助手。以下是用户现有的行程计划（JSON）：\n"
            f"{trip_json}\n\n"
            f"用户希望做的修改：{instruction}\n\n"
            "要求：\n"
            "1. 深刻理解指令（替换/新增/删除景点、增减天数、调整时间顺序、替换餐饮、调整预算或节奏等）。\n"
            "2. 返回修改后的【完整行程 JSON】，必须保持原有字段结构（title/city/days/route_type/crowd_type/budget_level/content 等），"
            "content 内每个 spot 至少保留 1 个 photo_spots，不得随意删减字段。\n"
            "3. 在返回 JSON 的顶层增加字段 \"reply\"，用一句话中文说明你做了哪些改动；"
            "若指令无法对应具体改动，请原样返回原行程并在 reply 中说明。\n"
            "4. 只输出 JSON，不要任何多余文字或解释。"
        )

    def _normalize_adjust(self, data: dict) -> dict:
        data.setdefault("title", "我的行程")
        data.setdefault("city", "杭州")
        data.setdefault("days", 2)
        data.setdefault("route_type", "popular")
        data.setdefault("crowd_type", "朋友")
        data.setdefault("budget_min", 500)
        data.setdefault("budget_max", 1500)
        _max = data.get("budget_max") or 1500
        data.setdefault("budget_level", "经济" if _max < 500 else "高端" if _max > 1500 else "舒适")
        content = data.setdefault("content", {})
        content.setdefault("itinerary", [])
        content.setdefault("total_budget", 0)
        content.setdefault("transport_plans", [])
        content.setdefault("budget_analysis", "")
        content.setdefault("preparations", [])
        for day in content["itinerary"]:
            day.setdefault("weather_tip", "")
            day.setdefault("season_tip", "")
            day.setdefault("crowd_tip", "")
            day.setdefault("spots", [])
            day.setdefault("meals", [])
            day.setdefault("transport", [])
            day.setdefault("budget", 0)
            day.setdefault("tips", "")
            for spot in day["spots"]:
                spot.setdefault("photo_spots", [])
                spot.setdefault("duration_min", 120)
                spot.setdefault("ticket_price", 0)
                spot.setdefault("best_price", spot.get("ticket_price", 0))
                spot.setdefault("ticket_channel", "")
                spot.setdefault("need_booking", False)
                spot.setdefault("official_account", "")
                spot.setdefault("description", "")
                spot.setdefault("category", "")
                spot.setdefault("address", "")
                for ps in spot["photo_spots"]:
                    ps.setdefault("position", "")
                    ps.setdefault("best_time", "")
                    ps.setdefault("tip", "")
                    ps.setdefault("avoid_crowd", "")
                    ps.setdefault("day_night", "")
                    ps.setdefault("suitable_for", "")
            for meal in day["meals"]:
                meal.setdefault("deal_channel", "")
                meal.setdefault("avg_price", 0)
                meal.setdefault("specialty", "")
                meal.setdefault("address", "")
                meal.setdefault("type", "lunch")
        return data


plan_service = PlanService()

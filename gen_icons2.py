#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重绘首页线性矢量图标：描边由 2px 减到 1.6px（更精致），保留渐变圆底。
输出 miniprogram/pages/index/icons.wxss，并打印 Hero 山形装饰的 base64。"""
import base64

STROKE = 1.6  # 更细的描边，质感更精致

# 服务图标：白色描边
SVC = {
    "map":   "<polygon points='3 11 21 3 14 21 11 14 3 11'/>",
    "car":   "<path d='M5 11l1.6-4.2A1.5 1.5 0 0 1 8 5.8h8a1.5 1.5 0 0 1 1.4 1.1L19 11'/><path d='M4 11h16v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z'/><circle cx='8' cy='17.5' r='1.6'/><circle cx='16' cy='17.5' r='1.6'/>",
    "hotel": "<path d='M3 18v-6a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v6'/><path d='M3 14h18'/><path d='M16 12h3a1 1 0 0 1 1 1v5'/><path d='M6 12V9.5A1.5 1.5 0 0 1 7.5 8h2'/>",
    "food":  "<path d='M6 3v7a2 2 0 0 0 4 0V3'/><path d='M8 3v18'/><path d='M17 3c-1.7 0-3 1.8-3 4s1.3 4 3 4'/><path d='M17 3v18'/><path d='M21 3c-1.7 0-3 1.8-3 4s1.3 4 3 4'/>",
    "flight":"<path d='M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3.5S18 3 16.5 4.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 2H4l-1 1 3 2 2 3 1-1v-3l2-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.3c.4-.2.6-.6.5-1.1z'/>",
    "ticket":"<path d='M3 9a3 3 0 0 0 0 6v2a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-2a3 3 0 0 0 0-6V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z'/><path d='M13 5v2'/><path d='M13 11v2'/><path d='M13 17v2'/>",
    "movie": "<path d='M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3z'/><path d='m6.2 5.3 3.1 3.9'/><path d='m12.4 3.4 3.1 4'/><path d='M3 11h18a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1z'/>",
    "takeout":"<path d='M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z'/><path d='M3 6h18'/><path d='M16 10a4 4 0 0 1-8 0'/>",
}

GI = {
    "form":  "<path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><path d='M14 2v6h6'/><path d='M8 13h8'/><path d='M8 17h8'/><path d='M8 9h2'/>",
    "quick": "<path d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/>",
    "ocr":   "<path d='M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3z'/><circle cx='12' cy='13' r='3'/>",
    "manual":"<rect x='3' y='3' width='7' height='7' rx='1.5'/><rect x='14' y='3' width='7' height='7' rx='1.5'/><rect x='14' y='14' width='7' height='7' rx='1.5'/><rect x='3' y='14' width='7' height='7' rx='1.5'/>",
}

# 各图标渐变（与之前保持一致）
SVC_GRAD = {
    "map": "linear-gradient(135deg, #60A5FA, #3B82F6)",
    "car": "linear-gradient(135deg, #FB923C, #F97316)",
    "hotel": "linear-gradient(135deg, #A78BFA, #8B5CF6)",
    "food": "linear-gradient(135deg, #F87171, #EF4444)",
    "flight": "linear-gradient(135deg, #38BDF8, #0EA5E9)",
    "ticket": "linear-gradient(135deg, #34D399, #10B981)",
    "movie": "linear-gradient(135deg, #818CF8, #6366F1)",
    "takeout": "linear-gradient(135deg, #FBBF24, #F59E0B)",
}
GI_GRAD = {
    "form": "linear-gradient(135deg, #60A5FA, #3B82F6)",
    "quick": "linear-gradient(135deg, #818CF8, #6366F1)",
    "ocr": "linear-gradient(135deg, #2DD4BF, #14B8A6)",
    "manual": "linear-gradient(135deg, #FB923C, #F97316)",
}

def b64(svg: str) -> str:
    return base64.b64encode(svg.encode()).decode()

def white_icon(paths: str) -> str:
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
           "stroke='#ffffff' stroke-width='%.1f' stroke-linecap='round' stroke-linejoin='round'>%s</svg>" % (STROKE, paths))
    return b64(svg)

def blue_icon(paths: str) -> str:
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
           "stroke='#3B82F6' stroke-width='%.1f' stroke-linecap='round' stroke-linejoin='round'>%s</svg>" % (STROKE, paths))
    return b64(svg)

lines = ["/* icons.wxss —— 线性矢量图标（自动生成，勿手改） */", ""]

# 定位 + 刷新（蓝色描边）
loc = blue_icon("<path d='M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z'/><circle cx='12' cy='10' r='3'/>")
ref = blue_icon("<path d='M21 12a9 9 0 1 1-2.64-6.36'/><polyline points='21 3 21 9 15 9'/>")
lines += [
    ".loc-ico {",
    "  width: 30rpx; height: 30rpx;",
    "  margin-right: 8rpx;",
    "  background-image: url(\"data:image/svg+xml;base64,%s\");" % loc,
    "  background-size: contain;",
    "  background-repeat: no-repeat;",
    "  background-position: center;",
    "}", "",
    ".refresh-ico {",
    "  width: 28rpx; height: 28rpx;",
    "  background-image: url(\"data:image/svg+xml;base64,%s\");" % ref,
    "  background-size: contain;",
    "  background-repeat: no-repeat;",
    "  background-position: center;",
    "  margin-right: 6rpx;",
    "}", "",
]

# 服务图标：白色 1.6px 描边 + 渐变圆底
for key, paths in SVC.items():
    enc = white_icon(paths)
    lines += [
        ".svc-ico.%s {" % key,
        "  background-image: url(\"data:image/svg+xml;base64,%s\"), %s;" % (enc, SVC_GRAD[key]),
        "  background-size: 44rpx 44rpx, cover;",
        "  background-repeat: no-repeat, no-repeat;",
        "  background-position: center, center;",
        "}", "",
    ]

# 规划入口图标
for key, paths in GI.items():
    enc = white_icon(paths)
    lines += [
        ".gi-ico.%s {" % key,
        "  background-image: url(\"data:image/svg+xml;base64,%s\"), %s;" % (enc, GI_GRAD[key]),
        "  background-size: 38rpx 38rpx, cover;",
        "  background-repeat: no-repeat, no-repeat;",
        "  background-position: center, center;",
        "}", "",
    ]

out = "\n".join(lines).rstrip() + "\n"
with open("miniprogram/pages/index/icons.wxss", "w", encoding="utf-8") as f:
    f.write(out)
print("icons.wxss written, %d bytes" % len(out))

# Hero 山形 + 太阳装饰（半透明白）
mountain = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 220 120' fill='none'>"
            "<circle cx='168' cy='34' r='15' fill='rgba(255,255,255,0.85)'/>"
            "<path d='M0 120 L46 60 L86 100 L120 52 L160 96 L220 58 L220 120 Z' fill='rgba(255,255,255,0.16)'/>"
            "<path d='M0 120 L70 84 L120 112 L180 78 L220 100 L220 120 Z' fill='rgba(255,255,255,0.10)'/>"
            "</svg>")
print("HERO_MOUNTAIN_B64=" + b64(mountain))

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 icons.wxss 提取图标 base64，生成与小程序首页 1:1 还原的 HTML 预览（rpx->px，750 画板缩放 0.5）。"""
import re, html

WXSS = "miniprogram/pages/index/icons.wxss"
css = open(WXSS, encoding="utf-8").read()

# 提取 .xxx { background-image: url("data:..."), <gradient>; ... }
# 用一个宽松的正则抓取每个类选择器块
blocks = re.findall(r"\.([a-zA-Z0-9_.-]+)\s*\{([^}]*)\}", css)
icons = {}  # name -> (b64, gradient)
for sel, body in blocks:
    mimg = re.search(r'url\("(data:image/svg\+xml;base64,[^"]+)"\)', body)
    if not mimg:
        continue
    b64 = mimg.group(1)
    mg = re.search(r",\s*(linear-gradient\([^)]*\))\s*;", body)
    grad = mg.group(1) if mg else "linear-gradient(135deg,#60A5FA,#3B82F6)"
    icons[sel] = (b64, grad)

# 服务/规划映射
svc = [("map","导航"),("car","打车"),("hotel","酒店"),("food","美食"),
       ("flight","机票高铁"),("ticket","景区门票"),("movie","电影票"),("takeout","外卖")]
gi  = [("plan-form","form","AI 表单规划","填表生成行程"),
       ("plan-quick","quick","一句话快规划","说句话，秒出方案"),
       ("plan-ocr","ocr","截图识行程","上传攻略图片"),
       ("plan-manual","manual","手动编排","自由拖拽编排")]

def svc_card(key, name):
    b64, grad = icons["svc-ico.%s" % key]
    return (f'<div class="svc-item"><div class="svc-ico" style="background-image:url(\'{b64}\'),{grad};'
            f'background-size:44px 44px,cover;background-repeat:no-repeat;background-position:center;"></div>'
            f'<div class="svc-name">{name}</div></div>')

def gi_card(cls, key, name, desc):
    b64, grad = icons["gi-ico.%s" % key]
    return (f'<div class="grid-item {("core" if key in ("form","quick") else "secondary")}">'
            f'<div class="gi-ico" style="background-image:url(\'{b64}\'),{grad};'
            f'background-size:38px 38px,cover;background-repeat:no-repeat;background-position:center;"></div>'
            f'<div class="gi-name">{name}</div><div class="gi-desc">{desc}</div></div>')

svc_html = "\n".join(svc_card(k,n) for k,n in svc)
gi_html  = "\n".join(gi_card(c,k,n,d) for c,k,n,d in gi)

# 山形装饰 base64（与 wxss 一致）
mountain = ("data:image/svg+xml;base64," +
    "PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyMjAgMTIwJyBmaWxsPSdub25lJz4"
    "8Y2lyY2xlIGN4PScxNjgnIGN5PSczNCcgcj0nMTUnIGZpbGw9J3JnYmEoMjU1LDI1NSwyNTUsMC44NSknLz48cGF0aCBkPSdNMCAxMjAgTDQ2IDYwIEw4NiAxMDAgTDEyMCA1MiBMMTYwIDk2IEwyMjAgNTggTDIyMCAxMjAgWicgZmlsbD0ncmdiYSgyNTUsMjU1LDI1NSwwLjE2KScvPjxwYXRoIGQ9J00wIDEyMCBMNzAgODQgTDEyMCAxMTIgTDE4MCA3OCBMMjIwIDEwMCBMMjIwIDEyMCBaJyBmaWxsPSdyZ2JhKDI1NSwyNTUsMjU1LDAuMTApJy8+PC9zdmc+")

hero_badge = '<div class="hero-badge"><span class="dot"></span>AI 智能规划</div>'

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>知途 AI 旅行 · 首页预览（升级版）</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background:#dfe6f1; display:flex; justify-content:center; padding:24px; font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; }}
  .frame {{ width:375px; }}
  .artboard {{ width:750px; transform:scale(0.5); transform-origin:top left; background:linear-gradient(180deg,#EAF2FF 0%,#F4F8FF 220px,#FFFFFF 560px); padding:0 32px 160px; position:relative; }}
  .navbar {{ position:absolute; top:0; left:0; right:0; height:88px; background:rgba(255,255,255,.96); border-bottom:1px solid rgba(0,0,0,.04); display:flex; align-items:center; justify-content:center; z-index:100; }}
  .navbar-title {{ display:flex; align-items:center; font-size:34px; font-weight:bold; color:#1f2937; }}
  .navbar-logo {{ width:48px; height:48px; border-radius:12px; margin-right:12px; box-shadow:0 2px 8px rgba(59,130,246,.15); background:#3B82F6; }}
  .header {{ display:flex; align-items:center; justify-content:space-between; padding:108px 0 20px; }}
  .welcome-text {{ font-size:34px; font-weight:700; color:#1f2937; }}
  .city-picker {{ display:flex; align-items:center; background:#fff; padding:14px 24px; border-radius:32px; font-size:26px; color:#1f2937; box-shadow:0 2px 12px rgba(59,130,246,.08); }}
  .hero {{ margin-top:8px; position:relative; border-radius:28px; padding:36px 32px 40px; overflow:hidden; color:#fff;
    background: radial-gradient(120% 120% at 0% 0%, #7CC0FF 0%, rgba(124,192,255,0) 55%), linear-gradient(135deg,#60A5FA,#2563EB 75%,#1E40AF);
    box-shadow:0 16px 36px rgba(37,99,235,.30), inset 0 2px 0 rgba(255,255,255,.25); }}
  .hero-badge {{ display:inline-flex; align-items:center; font-size:22px; font-weight:600; color:#EFF6FF; background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.30); padding:8px 18px; border-radius:999px; }}
  .hero-badge .dot {{ width:12px; height:12px; border-radius:50%; background:#7CF0C8; margin-right:10px; box-shadow:0 0 8px #7CF0C8; }}
  .hero-title {{ font-size:42px; font-weight:bold; letter-spacing:1px; margin-top:18px; }}
  .hero-sub {{ font-size:26px; opacity:.9; margin-top:12px; }}
  .hero-decor {{ position:absolute; right:-40px; bottom:-50px; width:260px; height:260px; border-radius:50%; background:radial-gradient(circle,rgba(255,255,255,.22),rgba(255,255,255,0) 70%); }}
  .hero-mountains {{ position:absolute; right:0; bottom:0; width:320px; height:175px; background-image:url('{mountain}'); background-size:contain; background-repeat:no-repeat; background-position:bottom right; }}
  .section {{ margin-top:36px; }}
  .sec-title {{ font-size:32px; font-weight:bold; color:#1f2937; margin-bottom:20px; }}
  .grid {{ display:flex; flex-wrap:wrap; gap:20px; }}
  .grid-item {{ width:calc(50% - 10px); border-radius:24px; padding:28px; display:flex; flex-direction:column; }}
  .grid-item.core {{ background:linear-gradient(160deg,rgba(219,234,254,.85),rgba(255,255,255,.95)); box-shadow:0 12px 28px rgba(59,130,246,.12), inset 0 1px 0 rgba(255,255,255,.6); }}
  .grid-item.secondary {{ background:#fff; border:2px solid #e5e7eb; box-shadow:0 10px 24px rgba(15,23,42,.05), inset 0 1px 0 rgba(255,255,255,.6); }}
  .gi-ico {{ width:76px; height:76px; border-radius:50%; margin-bottom:14px; position:relative;
    box-shadow:0 10px 22px rgba(59,130,246,.18), inset 0 -6px 10px rgba(0,0,0,.14), inset 0 4px 8px rgba(255,255,255,.35); }}
  .gi-ico::after {{ content:''; position:absolute; top:9px; left:13px; width:30px; height:18px; border-radius:50%;
    background:radial-gradient(circle at 35% 30%, rgba(255,255,255,.6), rgba(255,255,255,0) 70%); }}
  .gi-name {{ font-size:28px; font-weight:bold; color:#1f2937; }}
  .gi-desc {{ font-size:22px; margin-top:4px; color:#6b7280; }}
  .city-block {{ display:flex; align-items:center; background:#fff; border-radius:24px; padding:28px 32px; margin-top:28px; box-shadow:0 10px 24px rgba(15,23,42,.05), inset 0 1px 0 rgba(255,255,255,.6); }}
  .cb-label {{ font-size:28px; font-weight:bold; margin-right:20px; }}
  .cb-city {{ font-size:28px; font-weight:bold; }}
  .cb-arrow {{ margin-left:auto; color:#3B82F6; font-size:28px; }}
  .service-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:26px 16px; background:#fff; border-radius:24px; padding:32px 20px; box-shadow:0 10px 24px rgba(15,23,42,.05), inset 0 1px 0 rgba(255,255,255,.6); }}
  .svc-item {{ display:flex; flex-direction:column; align-items:center; }}
  .svc-ico {{ width:88px; height:88px; border-radius:50%; position:relative;
    box-shadow:0 10px 22px rgba(59,130,246,.18), inset 0 -6px 10px rgba(0,0,0,.14), inset 0 4px 8px rgba(255,255,255,.35); }}
  .svc-ico::after {{ content:''; position:absolute; top:11px; left:15px; width:34px; height:20px; border-radius:50%;
    background:radial-gradient(circle at 35% 30%, rgba(255,255,255,.6), rgba(255,255,255,0) 70%); }}
  .svc-name {{ font-size:22px; color:#4b5563; margin-top:10px; }}
  .tpl-scroll {{ display:flex; gap:24px; overflow:hidden; }}
  .tpl-card {{ width:320px; flex:0 0 320px; background:#fff; border-radius:24px; overflow:hidden; box-shadow:0 12px 28px rgba(59,130,246,.12), inset 0 1px 0 rgba(255,255,255,.6); }}
  .tpl-cover {{ height:160px; background:linear-gradient(135deg,#DBEAFE,#93C5FD); display:flex; align-items:center; justify-content:center; font-size:64px; }}
  .tpl-info {{ padding:20px; }}
  .tpl-name {{ font-size:28px; font-weight:bold; }}
  .tpl-meta {{ font-size:22px; color:#9ca3af; margin-top:8px; }}
  .tip {{ margin-top:28px; font-size:22px; color:#9ca3af; text-align:center; }}
</style></head>
<body><div class="frame"><div class="artboard">
  <div class="navbar">
    <div class="navbar-title"><div class="navbar-logo"></div>知途 AI 旅行</div>
  </div>
  <div class="header">
    <div class="welcome-text">发现你的下一站</div>
    <div class="city-picker">杭州 ▾</div>
  </div>
  <div class="hero">
    {hero_badge}
    <div class="hero-title">开始规划行程</div>
    <div class="hero-sub">AI 智能生成专属旅行路线</div>
    <div class="hero-decor"></div>
    <div class="hero-mountains"></div>
  </div>
  <div class="section"><div class="sec-title">开始规划</div><div class="grid">{gi_html}</div></div>
  <div class="city-block"><span class="cb-label">目的地</span><span class="cb-city">杭州</span><span class="cb-arrow">▾</span></div>
  <div class="section"><div class="sec-title">快捷服务</div><div class="service-grid">{svc_html}</div></div>
  <div class="section"><div class="sec-title">精选行程模板</div><div class="tpl-scroll">
    <div class="tpl-card"><div class="tpl-cover">🏔️</div><div class="tpl-info"><div class="tpl-name">杭州西湖两日游</div><div class="tpl-meta">杭州 · 2天 · 8景点</div></div></div>
    <div class="tpl-card"><div class="tpl-cover">🌊</div><div class="tpl-info"><div class="tpl-name">成都美食深度游</div><div class="tpl-meta">成都 · 3天 · 12景点</div></div></div>
  </div></div>
  <div class="tip">预览仅作视觉核对，真机请在微信开发者工具编译查看</div>
</div></div></body></html>"""

with open("outputs/index-redesign-final.html", "w", encoding="utf-8") as f:
    f.write(HTML)
print("preview written: outputs/index-redesign-final.html (%d bytes)" % len(HTML))
print("icons parsed:", len(icons))

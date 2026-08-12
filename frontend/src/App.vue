<script setup>
import { ref, onMounted } from 'vue'

const apiOk = ref(null)
const rootMsg = ref('')
const loading = ref(true)

async function check() {
  loading.value = true
  try {
    const h = await fetch('/api/health', { cache: 'no-store' })
    const hj = await h.json()
    apiOk.value = hj.status === 'ok'
  } catch (e) {
    apiOk.value = false
  }
  try {
    const r = await fetch('/', { cache: 'no-store' })
    const rj = await r.json()
    rootMsg.value = rj.message || ''
  } catch (e) {
    rootMsg.value = ''
  }
  loading.value = false
}

onMounted(check)
</script>

<template>
  <div class="wrap">
    <header class="hero">
      <div class="badge">知途 AI 旅行</div>
      <h1>全栈服务运行中</h1>
      <p class="sub">后端 API · MySQL · Redis · 容器编排状态自检面板</p>
    </header>

    <section class="card">
      <div class="row">
        <span class="label">后端 API（/api/health）</span>
        <span class="dot" :class="apiOk === null ? 'wait' : apiOk ? 'ok' : 'bad'">
          {{ apiOk === null ? '检测中…' : apiOk ? '正常' : '异常' }}
        </span>
      </div>
      <div class="row">
        <span class="label">服务信息（/）</span>
        <span class="val">{{ rootMsg || '—' }}</span>
      </div>
      <button class="btn" @click="check" :disabled="loading">重新检测</button>
    </section>

    <section class="card tips">
      <h3>使用说明</h3>
      <ul>
        <li>用户端为微信小程序，通过 HTTPS 调用本后端 API（<code>/api/*</code>）。</li>
        <li>本页面为运维自检面板，确认容器与服务健康。</li>
        <li>数据库 / Redis / 后端端口仅在内网，未对公网开放。</li>
        <li>接口文档：<code>/docs</code>（Swagger UI）。</li>
      </ul>
    </section>

    <footer class="foot">知途 AI 旅行 · Docker Compose 部署 · 腾讯云轻量应用服务器</footer>
  </div>
</template>

<style scoped>
.wrap { max-width: 720px; margin: 0 auto; padding: 48rpx 28rpx 60rpx; }
.hero { text-align: center; margin-bottom: 36rpx; }
.badge {
  display: inline-block; font-size: 22rpx; font-weight: 600; color: #2563eb;
  background: rgba(37, 99, 235, 0.1); padding: 8rpx 20rpx; border-radius: 999rpx;
}
.hero h1 { font-size: 44rpx; font-weight: 700; margin: 18rpx 0 8rpx; }
.sub { font-size: 24rpx; color: #6b7280; }
.card {
  background: #fff; border-radius: 24rpx; padding: 32rpx; margin-bottom: 24rpx;
  box-shadow: 0 10rpx 30rpx rgba(37, 99, 235, 0.08);
}
.row { display: flex; align-items: center; justify-content: space-between; padding: 16rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.row:last-of-type { border-bottom: none; }
.label { font-size: 26rpx; color: #374151; }
.val { font-size: 24rpx; color: #6b7280; max-width: 60%; text-align: right; }
.dot { font-size: 24rpx; font-weight: 600; padding: 6rpx 18rpx; border-radius: 999rpx; }
.dot.ok { color: #047857; background: #d1fae5; }
.dot.bad { color: #b91c1c; background: #fee2e2; }
.dot.wait { color: #92400e; background: #fef3c7; }
.btn {
  margin-top: 24rpx; width: 100%; padding: 20rpx; border: none; border-radius: 16rpx;
  background: linear-gradient(135deg, #60a5fa, #2563eb); color: #fff; font-size: 28rpx; font-weight: 600;
}
.btn:active { transform: scale(0.98); }
.tips h3 { font-size: 28rpx; margin-bottom: 16rpx; }
.tips ul { padding-left: 32rpx; }
.tips li { font-size: 24rpx; color: #4b5563; line-height: 1.9; }
.tips code { background: #f1f5f9; padding: 2rpx 8rpx; border-radius: 6rpx; font-size: 22rpx; }
.foot { text-align: center; font-size: 22rpx; color: #9ca3af; margin-top: 20rpx; }
</style>

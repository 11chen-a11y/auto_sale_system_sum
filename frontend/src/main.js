import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './style.css'

const app = createApp(App)

// 全局错误捕获：未处理异常会被记录到控制台，避免静默
app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue全局错误]', err, info)
}

// 兜底捕获未处理的 promise 拒绝
window.addEventListener('unhandledrejection', event => {
  console.error('[未处理的Promise拒绝]', event.reason)
})

app.use(createPinia()).use(router).mount('#app')
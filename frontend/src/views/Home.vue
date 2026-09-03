<script setup>
import { ref, computed, watch, onMounted, defineAsyncComponent } from 'vue'
import { useUserStore } from '../stores/user'
import BatchImportModal from '../components/BatchImportModal.vue'

const store = useUserStore()
const active = ref('')
const collapsed = ref(false)
const showBatchImport = ref(false)
onMounted(() => { if (!store.userInfo) store.fetchUser() })

const isAdmin = computed(() => store.userInfo?.role === 'admin')

const pageComponents = {
  node_price: defineAsyncComponent(() => import('./NodePrice.vue')),
  load_data: defineAsyncComponent(() => import('./LoadData.vue')),
  new_energy: defineAsyncComponent(() => import('./NewEnergy.vue')),
  generator: defineAsyncComponent(() => import('./Generator.vue')),
  trade: defineAsyncComponent(() => import('./TradeManage.vue')),
  customer: defineAsyncComponent(() => import('./Customer.vue')),
  bill: defineAsyncComponent(() => import('./Bill.vue')),
  contract: defineAsyncComponent(() => import('./Contract.vue')),
  settlement: defineAsyncComponent(() => import('./Settlement.vue')),
  load_forecast: defineAsyncComponent(() => import('./LoadForecast.vue')),
  analysis_center: defineAsyncComponent(() => import('./AnalysisCenter.vue')),
  user_manage: defineAsyncComponent(() => import('./UserManage.vue')),
}
const activeComp = computed(() => (menu.value.some(m => m.key === active.value) ? pageComponents[active.value] : null))

// 公开市场数据：所有登录用户可见（只读）
const marketMenu = [
  { key: 'node_price', icon: '⚡', label: '节点电价' },
  { key: 'load_data', icon: '📊', label: '负荷数据' },
  { key: 'analysis_center', icon: '📉', label: '数据分析' },
]
// 业务功能模块：仅管理员可见
const moduleMenu = [
  { key: 'new_energy', icon: '🔋', label: '绿电管理' },
  { key: 'generator', icon: '🏭', label: '发电商管理' },
  { key: 'trade', icon: '💹', label: '交易管理' },
  { key: 'customer', icon: '👥', label: '客户档案' },
  { key: 'bill', icon: '📋', label: '账单管理' },
  { key: 'contract', icon: '📝', label: '合约管理' },
  { key: 'settlement', icon: '🧾', label: '交易结算' },
  { key: 'load_forecast', icon: '📈', label: '负荷预测' },
]
// 管理员专属菜单
const adminMenu = [
  { key: 'user_manage', icon: '👤', label: '用户管理' },
]

const menu = computed(() => (isAdmin.value ? [...marketMenu, ...moduleMenu, ...adminMenu] : [...marketMenu]))

watch(isAdmin, () => {
  if (!menu.value.some(m => m.key === active.value)) active.value = 'node_price'
}, { immediate: true })
</script>

<template>
  <div class="layout" :class="{ collapsed }">
    <!-- 常驻小按钮 -->
    <button class="toggle" @click="collapsed = !collapsed">
      <span>{{ collapsed ? '›' : '‹' }}</span>
    </button>

    <aside v-show="!collapsed">
      <div class="logo"><span class="mi">⚡</span><span class="logo-text">售电管理</span></div>
      <nav>
        <button v-for="m in menu" :key="m.key" :class="{ on: active === m.key }" @click="active = m.key">
          <span class="mi">{{ m.icon }}</span><span>{{ m.label }}</span>
        </button>
      </nav>
      <div class="sidebar-footer">
        <div v-if="store.userInfo" class="user-info">
          <div class="uname">{{ store.userInfo.username }}</div>
          <div class="urole">{{ store.userInfo.role }}</div>
        </div>
        <button class="btn btn-ghost sm" @click="store.logout"><span>退出</span></button>
      </div>
    </aside>

    <main>
      <div class="page-head">
        <h1>{{ menu.find(m => m.key === active)?.label || '无访问权限' }}</h1>
        <div class="badge" v-if="active">{{ active }}</div>
        <button v-if="isAdmin" class="btn btn-ghost sm batch-btn" @click="showBatchImport = true">📥 批量导入</button>
      </div>
      <div class="content-card">
        <component v-if="activeComp" :is="activeComp" :key="active" />
        <div v-else class="placeholder">您的账号没有权限访问该功能模块，请联系管理员开通权限。</div>
      </div>
    </main>

    <BatchImportModal v-if="showBatchImport" @close="showBatchImport = false" @imported="showBatchImport = false" />
  </div>
</template>

<style scoped>
.layout { position: relative; z-index: 10; display: flex; min-height: 100vh; }

.toggle {
  position: fixed;
  top: 22px;
  z-index: 30;
  width: 28px;
  height: 28px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--t3);
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color .2s, left .2s;
  left: 174px;
}
.toggle:hover { color: var(--cyan); }
.collapsed .toggle { left: 14px; }

aside {
  width: 200px;
  background: var(--surface);
  backdrop-filter: blur(30px) saturate(2);
  border-right: 1px solid var(--border);
  padding: 24px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: fixed;
  top: 0; bottom: 0; left: 0;
}

.logo { display: flex; align-items: center; justify-content: center; gap: 8px; padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 16px; width: 100%; }
.logo-text { font-family: 'Cormorant Garamond', serif; font-size: 1.2rem; font-weight: 400; letter-spacing: .06em; background: linear-gradient(135deg, var(--cyan-b), var(--cyan)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }

nav { flex: 1; display: flex; flex-direction: column; gap: 4px; width: 100%; }

nav button {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  padding: 11px 8px; background: transparent; border: none; border-radius: 12px;
  color: var(--t2); font-family: 'Outfit', sans-serif; font-size: 13px; font-weight: 300;
  cursor: pointer; transition: background .2s, color .2s; white-space: nowrap; width: 100%;
}
nav button:hover { background: rgba(255,255,255,.03); color: var(--t1); }
nav button.on { background: linear-gradient(135deg, rgba(255,123,156,.12), rgba(255,123,156,.04)); color: var(--cyan); font-weight: 400; border: 1px solid rgba(255,123,156,.2); }

.mi { font-size: 16px; flex-shrink: 0; }

.sidebar-footer { border-top: 1px solid var(--border); padding-top: 14px; width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; }
.user-info { flex: 1; min-width: 0; }
.uname { font-size: 13px; font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.urole { font-size: 11px; color: var(--t3); }
.sm { padding: 8px 12px; font-size: 12px; flex-shrink: 0; }

main { flex: 1; margin-left: 200px; padding: 40px; transition: margin-left .2s; }
.collapsed main { margin-left: 0; }

.page-head { display: flex; align-items: center; gap: 16px; margin-bottom: 32px; }
.page-head h1 { font-family: 'Cormorant Garamond', serif; font-size: 2rem; font-weight: 300; color: var(--t1); }
.badge { display: inline-flex; padding: 4px 14px; background: rgba(255,123,156,.1); border: 1px solid rgba(255,123,156,.2); border-radius: 100px; font-size: .6rem; font-weight: 600; letter-spacing: .15em; color: var(--cyan); }
.batch-btn { margin-left: auto; }

.content-card { background: var(--surface); backdrop-filter: blur(20px); border: 1px solid var(--border); border-radius: var(--r); padding: 48px; }
.placeholder { color: var(--t3); font-weight: 300; text-align: center; }
</style>

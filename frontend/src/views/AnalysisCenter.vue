<script setup>
import { ref, watch, computed, defineAsyncComponent } from 'vue'
import { useUserStore } from '../stores/user'

const store = useUserStore()
const isAdmin = computed(() => store.userInfo?.role === 'admin')

const PriceTrend = defineAsyncComponent(() => import('./PriceTrend.vue'))
const Analysis = defineAsyncComponent(() => import('./Analysis.vue'))
const tab = ref('trend')

// 非管理员只看价格趋势，关联分析接口是管理员权限
watch(isAdmin, v => {
  if (!v && tab.value === 'analysis') tab.value = 'trend'
})
</script>

<template>
  <div class="ac-root">
    <div class="tabs">
      <button :class="{ on: tab === 'trend' }" @click="tab = 'trend'">价格趋势</button>
      <button v-if="isAdmin" :class="{ on: tab === 'analysis' }" @click="tab = 'analysis'">关联分析</button>
    </div>
    <PriceTrend v-if="tab === 'trend'" />
    <Analysis v-else-if="tab === 'analysis' && isAdmin" />
  </div>
</template>

<style scoped>
.ac-root { display: flex; flex-direction: column; gap: 24px; }
</style>

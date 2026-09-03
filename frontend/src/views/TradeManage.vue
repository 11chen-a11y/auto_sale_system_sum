<script setup>
import { ref, defineAsyncComponent } from 'vue'

const SpotTrade = defineAsyncComponent(() => import('./SpotTrade.vue'))
const PowerBid = defineAsyncComponent(() => import('./PowerBid.vue'))
const tab = ref('spot')
</script>

<template>
  <div class="tm-root">
    <div class="tabs">
      <button :class="{ on: tab === 'spot' }" @click="tab = 'spot'">现货交易</button>
      <button :class="{ on: tab === 'bid' }" @click="tab = 'bid'">报价/竞价</button>
    </div>
    <SpotTrade v-if="tab === 'spot'" />
    <PowerBid v-else />
  </div>
</template>

<style scoped>
.tm-root { display: flex; flex-direction: column; gap: 24px; }
</style>

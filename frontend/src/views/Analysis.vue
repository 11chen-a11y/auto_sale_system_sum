<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { getLoadVsPrice, getLoadVsNewEnergy, getLoadVsWeather, getCustomerConsumption, getFullChain } from '../api/analysis'
import { getDates as getLoadDates } from '../api/nodePrice'
import { showError } from '../utils/error'

const activeTab = ref('load_price')
const chartEl = ref(null)
let chart = null

const tabs = [
  { key: 'load_price', label: '负荷 vs 电价' },
  { key: 'load_ne', label: '负荷 vs 新能源' },
  { key: 'load_weather', label: '负荷 vs 天气' },
  { key: 'customer', label: '客户用电' },
  { key: 'full_chain', label: '完整链路' },
]

// ─── 可选日期 ───
const allDates = ref([])

// ─── 负荷 vs 电价 ───
const lpDate = ref('')
const lpData = ref(null)

async function loadLP() {
  if (!lpDate.value) return
  const res = await getLoadVsPrice({ record_date: lpDate.value })
  lpData.value = res.data
}

function renderLP() {
  if (!chartEl.value || !lpData.value) return
  nextTick(() => {
    if (!chart) chart = echarts.init(chartEl.value)
    const labels = Array.from({ length: 96 }, (_, i) => {
      const h = String(Math.floor(i / 4)).padStart(2, '0')
      const m = String((i % 4) * 15).padStart(2, '0')
      return `${h}:${m}`
    })
    const loadSeries = (lpData.value.load || []).map(r => ({
      name: `负荷 (${r.data_type})`,
      type: 'line',
      smooth: true,
      data: r.slots ? Object.values(r.slots).map(Number) : [],
      yAxisIndex: 0,
      symbol: 'none',
      lineStyle: { width: 2, color: '#ff7b9c' },
      itemStyle: { color: '#ff7b9c' },
    }))
    const priceSeries = (lpData.value.price || []).map(r => ({
      name: `电价 (${r.node_name}${r.price_type ? '-' + r.price_type : ''})`,
      type: 'line',
      smooth: true,
      data: r.slots ? Object.values(r.slots).map(Number) : [],
      yAxisIndex: 1,
      symbol: 'none',
      lineStyle: { width: 2, color: '#e8577a' },
      itemStyle: { color: '#e8577a' },
    }))
    const allSeries = [...loadSeries, ...priceSeries]
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: allSeries.map(s => s.name), textStyle: { color: '#a38990' }, bottom: 0 },
      grid: { left: 60, right: 60, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#a38990', fontSize: 10, interval: 11 } },
      yAxis: [
        { type: 'value', name: '负荷 (MW)', nameTextStyle: { color: '#ff7b9c' }, axisLabel: { color: '#a38990' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
        { type: 'value', name: '电价 (元/MWh)', nameTextStyle: { color: '#e8577a' }, axisLabel: { color: '#a38990' }, splitLine: { show: false } },
      ],
      series: allSeries,
      backgroundColor: 'transparent',
    })
    chart.resize()
  })
}
watch(lpData, renderLP, { deep: true })

// ─── 负荷 vs 新能源 ───
const neDate = ref('')
const neData = ref(null)

async function loadNE() {
  if (!neDate.value) return
  const res = await getLoadVsNewEnergy({ record_date: neDate.value })
  neData.value = res.data
}

function renderNE() {
  if (!chartEl.value || !neData.value) return
  nextTick(() => {
    if (!chart) chart = echarts.init(chartEl.value)
    const labels = Array.from({ length: 96 }, (_, i) => {
      const h = String(Math.floor(i / 4)).padStart(2, '0')
      const m = String((i % 4) * 15).padStart(2, '0')
      return `${h}:${m}`
    })
    const series = []
    ;(neData.value.load || []).forEach(r => {
      series.push({ name: `负荷 (${r.data_type})`, type: 'line', smooth: true, data: r.slots ? Object.values(r.slots).map(Number) : [], symbol: 'none', lineStyle: { width: 2, color: '#ff7b9c' } })
    })
    ;(neData.value.new_energy || []).forEach(r => {
      const slots = r.actual_slots || {}
      series.push({ name: `新能源 (${r.station_name})`, type: 'line', smooth: true, data: Object.values(slots).map(Number), symbol: 'none', lineStyle: { width: 2, color: '#c48bb8', type: 'dashed' } })
    })
    if (neData.value.net_load) {
      series.push({ name: '净负荷', type: 'line', smooth: true, data: Object.values(neData.value.net_load).map(Number), symbol: 'none', lineStyle: { width: 3, color: '#ffd54f' }, areaStyle: { color: 'rgba(255,213,79,0.08)' } })
    }
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: series.map(s => s.name), textStyle: { color: '#a38990' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#a38990', fontSize: 10, interval: 11 } },
      yAxis: { type: 'value', name: 'MW', nameTextStyle: { color: '#a38990' }, axisLabel: { color: '#a38990' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series, backgroundColor: 'transparent',
    })
    chart.resize()
  })
}
watch(neData, renderNE, { deep: true })

// ─── 负荷 vs 天气 ───
const wFrom = ref('')
const wTo = ref('')
const wData = ref(null)

async function loadWeather() {
  if (!wFrom.value || !wTo.value) return
  const res = await getLoadVsWeather({ date_from: wFrom.value, date_to: wTo.value })
  wData.value = res.data
}

function renderWeather() {
  if (!chartEl.value || !wData.value) return
  nextTick(() => {
    if (!chart) chart = echarts.init(chartEl.value)
    const points = wData.value.points || []
    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: p => `<div style="font-weight:600">${p.data[0]}</div>日均负荷: ${p.data[1].toFixed(2)} MW<br/>日均温度: ${p.data[2].toFixed(1)}°C`,
      },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'value', name: '日均温度 (°C)', nameTextStyle: { color: '#a38990' }, axisLabel: { color: '#a38990' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      yAxis: { type: 'value', name: '日均负荷 (MW)', nameTextStyle: { color: '#a38990' }, axisLabel: { color: '#a38990' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series: [{
        type: 'scatter',
        data: points.map(p => [p.avg_temp, p.avg_load, p.date]),
        symbolSize: 10,
        itemStyle: { color: '#ff7b9c' },
      }],
      backgroundColor: 'transparent',
    })
    chart.resize()
  })
}
watch(wData, renderWeather, { deep: true })

// ─── 客户用电 ───
const custMonth = ref('')
const custMonths = ref([])
const custData = ref(null)

async function loadCustomer() {
  const res = await getCustomerConsumption({ year_month: custMonth.value || undefined })
  custData.value = res.data
  if (res.data.available_months) custMonths.value = res.data.available_months
  if (!custMonth.value && custMonths.value.length) custMonth.value = custMonths.value[0]
}

function renderCustomer() {
  if (!chartEl.value || !custData.value) return
  nextTick(() => {
    if (!chart) chart = echarts.init(chartEl.value)
    const items = custData.value.items || []
    const names = items.map(r => r.customer_name)
    const kwh = items.map(r => r.total_kwh)
    const amount = items.map(r => r.total_amount)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['用电量 (kWh)', '电费 (元)'], textStyle: { color: '#a38990' }, bottom: 0 },
      grid: { left: 60, right: 60, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: names, axisLabel: { color: '#a38990', rotate: 20 } },
      yAxis: [
        { type: 'value', name: 'kWh', nameTextStyle: { color: '#a38990' }, axisLabel: { color: '#a38990' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
        { type: 'value', name: '元', nameTextStyle: { color: '#e8577a' }, axisLabel: { color: '#a38990' }, splitLine: { show: false } },
      ],
      series: [
        { name: '用电量 (kWh)', type: 'bar', data: kwh, itemStyle: { color: '#ff7b9c' } },
        { name: '电费 (元)', type: 'line', yAxisIndex: 1, data: amount, symbol: 'none', lineStyle: { color: '#e8577a', width: 2 } },
      ],
      backgroundColor: 'transparent',
    })
    chart.resize()
  })
}
watch(custData, renderCustomer, { deep: true })

// ─── 完整链路 ───
const chainDate = ref('')
const chainData = ref(null)

async function loadChain() {
  if (!chainDate.value) return
  const res = await getFullChain({ record_date: chainDate.value })
  chainData.value = res.data
}

function renderChain() {
  if (!chartEl.value || !chainData.value) return
  nextTick(() => {
    if (!chart) chart = echarts.init(chartEl.value)
    const labels = Array.from({ length: 96 }, (_, i) => {
      const h = String(Math.floor(i / 4)).padStart(2, '0')
      const m = String((i % 4) * 15).padStart(2, '0')
      return `${h}:${m}`
    })
    const d = chainData.value
    const series = []
    const colors = ['#ff7b9c', '#c48bb8', '#ffd54f', '#e8577a']
    let ci = 0
    ;(d.load || []).forEach(r => {
      series.push({ name: `负荷 (${r.data_type})`, type: 'line', smooth: true, data: r.slots ? Object.values(r.slots).map(Number) : [], symbol: 'none', lineStyle: { width: 2, color: colors[ci % colors.length] } })
      ci++
    })
    ;(d.new_energy || []).forEach(r => {
      series.push({ name: `新能源 (${r.station_name})`, type: 'line', smooth: true, data: r.actual_slots ? Object.values(r.actual_slots).map(Number) : [], symbol: 'none', lineStyle: { width: 2, color: colors[ci % colors.length], type: 'dashed' } })
      ci++
    })
    ;(d.price || []).forEach(r => {
      series.push({ name: `电价 (${r.node_name})`, type: 'line', smooth: true, data: r.slots ? Object.values(r.slots).map(Number) : [], symbol: 'none', lineStyle: { width: 2, color: colors[ci % colors.length] } })
      ci++
    })
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: series.map(s => s.name), textStyle: { color: '#a38990' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#a38990', fontSize: 10, interval: 11 } },
      yAxis: { type: 'value', name: 'MW / 元/MWh', nameTextStyle: { color: '#a38990' }, axisLabel: { color: '#a38990' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series, backgroundColor: 'transparent',
    })
    chart.resize()
  })
}
watch(chainData, renderChain, { deep: true })

// ─── 日期选择切换时的图表容器重置 ───
watch(activeTab, () => { chart = null })

// ─── 初始化 ───
onMounted(async () => {
  try {
    const d = await getLoadDates()
    allDates.value = d.data
  } catch (e) { showError(e) }
})
</script>

<template>
  <div class="analysis-root">
    <div class="tabs-bar">
      <button v-for="t in tabs" :key="t.key" :class="{ on: activeTab === t.key }" @click="activeTab = t.key">
        {{ t.label }}
      </button>
    </div>

    <!-- 负荷 vs 电价 -->
    <div v-show="activeTab === 'load_price'" class="tab-content">
      <div class="ctrl-bar">
        <select v-model="lpDate">
          <option value="">选择日期</option>
          <option v-for="d in allDates" :key="d" :value="d">{{ d }}</option>
        </select>
        <button class="btn btn-primary" @click="loadLP">查询</button>
      </div>
      <div class="desc">左轴：负荷 (MW) &nbsp;|&nbsp; 右轴：电价 (元/MWh)</div>
      <div class="chart-box" ref="chartEl" v-show="lpData"></div>
      <div v-if="!lpData" class="chart-placeholder">选择日期后查询</div>
    </div>

    <!-- 负荷 vs 新能源 -->
    <div v-show="activeTab === 'load_ne'" class="tab-content">
      <div class="ctrl-bar">
        <select v-model="neDate">
          <option value="">选择日期</option>
          <option v-for="d in allDates" :key="d" :value="d">{{ d }}</option>
        </select>
        <button class="btn btn-primary" @click="loadNE">查询</button>
      </div>
      <div class="desc">净负荷 = 总负荷 - 新能源出力（黄色区域）</div>
      <div class="chart-box" ref="chartEl" v-show="neData"></div>
      <div v-if="!neData" class="chart-placeholder">选择日期后查询</div>
    </div>

    <!-- 负荷 vs 天气 -->
    <div v-show="activeTab === 'load_weather'" class="tab-content">
      <div class="ctrl-bar">
        <input v-model="wFrom" type="date" />
        <span>至</span>
        <input v-model="wTo" type="date" />
        <button class="btn btn-primary" @click="loadWeather">查询</button>
      </div>
      <div class="desc">散点图：每个点代表一天的日均负荷和日均温度</div>
      <div class="chart-box" ref="chartEl" v-show="wData"></div>
      <div v-if="!wData" class="chart-placeholder">选择日期范围后查询</div>
    </div>

    <!-- 客户用电 -->
    <div v-show="activeTab === 'customer'" class="tab-content">
      <div class="ctrl-bar">
        <select v-model="custMonth">
          <option value="">全部月份</option>
          <option v-for="m in custMonths" :key="m" :value="m">{{ m }}</option>
        </select>
        <button class="btn btn-primary" @click="loadCustomer">查询</button>
      </div>
      <div class="chart-box" ref="chartEl" v-show="custData"></div>
      <div v-if="!custData" class="chart-placeholder">查询后展示</div>
      <div class="table-wrap" v-if="custData && custData.items.length">
        <table>
          <thead><tr><th>客户</th><th>类型</th><th>电压等级</th><th>月份</th><th>用电量 (kWh)</th><th>电费 (元)</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="r in custData.items" :key="r.customer_id + r.bill_month">
              <td>{{ r.customer_name }}</td>
              <td>{{ r.customer_type || '-' }}</td>
              <td>{{ r.voltage_level || '-' }}</td>
              <td>{{ r.bill_month }}</td>
              <td>{{ Number(r.total_kwh).toLocaleString() }}</td>
              <td>{{ Number(r.total_amount).toLocaleString() }}</td>
              <td><span class="tag" :class="{ paid: r.payment_status === '已付', unpaid: r.payment_status === '未付' }">{{ r.payment_status }}</span></td>
            </tr>
            <tr v-if="!custData.items.length"><td colspan="7" class="empty">暂无数据</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 完整链路 -->
    <div v-show="activeTab === 'full_chain'" class="tab-content">
      <div class="ctrl-bar">
        <select v-model="chainDate">
          <option value="">选择日期</option>
          <option v-for="d in allDates" :key="d" :value="d">{{ d }}</option>
        </select>
        <button class="btn btn-primary" @click="loadChain">查询</button>
      </div>
      <div class="desc">同一日期下，天气 → 负荷 → 新能源出力 → 电价 全链路展示</div>
      <div class="chart-box" ref="chartEl" v-show="chainData"></div>
      <div v-if="!chainData" class="chart-placeholder">选择日期后查询</div>

      <div class="chain-info" v-if="chainData">
        <div class="info-card" v-if="chainData.weather && chainData.weather.length">
          <h4>天气</h4>
          <div v-for="w in chainData.weather" :key="w.station_name">
            {{ w.city || w.station_name }}: {{ w.data_type }} {{ w.temperature }}°C
          </div>
        </div>
        <div class="info-card" v-if="chainData.load && chainData.load.length">
          <h4>负荷</h4>
          <div v-for="r in chainData.load" :key="r.data_type">{{ r.data_type }} — {{ r.slots ? Object.values(r.slots).reduce((a: number, b: any) => a + Number(b), 0).toFixed(2) : 0 }} MWh</div>
        </div>
        <div class="info-card" v-if="chainData.new_energy && chainData.new_energy.length">
          <h4>新能源</h4>
          <div v-for="r in chainData.new_energy" :key="r.station_name">{{ r.station_name }} ({{ r.energy_type }}) — {{ r.actual_slots ? Object.values(r.actual_slots).reduce((a: number, b: any) => a + Number(b), 0).toFixed(2) : 0 }} MWh</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analysis-root { display: flex; flex-direction: column; gap: 20px; }

.tabs-bar { display: flex; gap: 4px; background: rgba(255,105,135,.04); border: 1px solid var(--border); border-radius: 12px; padding: 4px; overflow-x: auto; }
.tabs-bar button { flex: 1; padding: 10px 16px; border: none; border-radius: 10px; background: transparent; color: var(--t3); font-family: 'Outfit', sans-serif; font-size: 13px; cursor: pointer; white-space: nowrap; transition: all .3s; }
.tabs-bar button.on { background: linear-gradient(135deg, var(--cyan), var(--cyan-d)); color: #fff; font-weight: 500; }

.tab-content { display: flex; flex-direction: column; gap: 16px; }

.ctrl-bar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.ctrl-bar select, .ctrl-bar input {
  padding: 8px 12px; background: rgba(255,105,135,.04); border: 1px solid var(--border);
  border-radius: 8px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.ctrl-bar select option { background: #fff5f7; }
.ctrl-bar .btn { padding: 8px 20px; font-size: 13px; }
.ctrl-bar span { color: var(--t3); font-size: 13px; }

.desc { font-size: 12px; color: var(--t3); font-weight: 300; }

.chart-box { height: 400px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 20px; }
.chart-placeholder { height: 400px; display: flex; align-items: center; justify-content: center; color: var(--t3); font-weight: 300; background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); }

.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 20px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 600; letter-spacing: .08em; color: var(--t3); border-bottom: 1px solid var(--border); }
td { padding: 10px 12px; font-size: 13px; color: var(--t2); border-bottom: 1px solid rgba(255,105,135,.06); white-space: nowrap; }
tr:hover td { background: rgba(255,105,135,.04); }
.tag { display: inline-block; padding: 2px 10px; border-radius: 100px; font-size: 11px; background: rgba(255,105,135,.08); color: var(--t3); }
.tag.paid { background: rgba(255,123,156,.12); color: var(--cyan); }
.tag.unpaid { background: rgba(255,77,106,.1); color: var(--danger); }
.empty { text-align: center; color: var(--t3); padding: 32px !important; }

.chain-info { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.info-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 16px; }
.info-card h4 { font-size: 13px; font-weight: 500; color: var(--cyan); margin-bottom: 8px; }
.info-card div { font-size: 12px; color: var(--t2); line-height: 1.8; }

.btn { padding: 8px 20px; border: none; border-radius: 14px; font-family: 'Outfit', sans-serif; font-size: 13px; font-weight: 500; cursor: pointer; transition: all .4s var(--e); position: relative; overflow: hidden; letter-spacing: .02em; }
.btn-primary { background: linear-gradient(135deg, var(--cyan), var(--cyan-d)); color: #fff; }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 30px var(--cyan-g); }
</style>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getTrend, getComparison, getSpotTrend, getVolatility, getSeasonal, getCorrelation } from '../api/priceTrend'
import { showError } from '../utils/error'

const tab = ref('trend')
const dateFrom = ref('')
const dateTo = ref('')
const nodeName = ref('')
const priceType = ref('')
const nodesText = ref('')
const tradeType = ref('')
const seasonalYear = ref('')
const seasonalNode = ref('')

const trendData = ref(null)
const comparisonData = ref(null)
const spotData = ref(null)
const volatilityData = ref(null)
const seasonalData = ref(null)

const loading = ref(false)
const trendChartEl = ref(null)
const comparisonChartEl = ref(null)
const spotChartEl = ref(null)
const volatilityChartEl = ref(null)
const seasonalChartEl = ref(null)
let trendChart = null
let comparisonChart = null
let spotChart = null
let volatilityChart = null
let seasonalChart = null

function today() { return new Date().toISOString().slice(0, 10) }

onMounted(() => {
  const d = today()
  dateTo.value = d
  const past = new Date()
  past.setDate(past.getDate() - 30)
  dateFrom.value = past.toISOString().slice(0, 10)
  nodesText.value = ''
  seasonalYear.value = new Date().getFullYear().toString()
  loadTrend()
})

async function loadTrend() {
  if (!dateFrom.value || !dateTo.value) return
  loading.value = true
  try {
    const params = { date_from: dateFrom.value, date_to: dateTo.value }
    if (nodeName.value) params.node_name = nodeName.value
    if (priceType.value) params.price_type = priceType.value
    const res = await getTrend(params)
    trendData.value = res.data
  } catch (e) { trendData.value = null; showError(e) }
  finally { loading.value = false }
}

async function loadComparison() {
  if (!dateFrom.value || !dateTo.value) return
  loading.value = true
  try {
    const params = { date_from: dateFrom.value, date_to: dateTo.value }
    if (nodesText.value.trim()) params.nodes = nodesText.value.trim()
    const res = await getComparison(params)
    comparisonData.value = res.data
  } catch (e) { comparisonData.value = null; showError(e) }
  finally { loading.value = false }
}

async function loadSpot() {
  loading.value = true
  try {
    const params = {}
    if (tradeType.value) params.trade_type = tradeType.value
    const res = await getSpotTrend(params)
    spotData.value = res.data
  } catch (e) { spotData.value = null; showError(e) }
  finally { loading.value = false }
}

async function loadVolatility() {
  if (!dateFrom.value || !dateTo.value) return
  loading.value = true
  try {
    const params = { date_from: dateFrom.value, date_to: dateTo.value }
    if (nodeName.value) params.node_name = nodeName.value
    if (priceType.value) params.price_type = priceType.value
    const res = await getVolatility(params)
    volatilityData.value = res.data
  } catch (e) { volatilityData.value = null; showError(e) }
  finally { loading.value = false }
}

async function loadSeasonal() {
  loading.value = true
  try {
    const params = {}
    if (seasonalYear.value) params.year = parseInt(seasonalYear.value)
    if (seasonalNode.value) params.node_name = seasonalNode.value
    const res = await getSeasonal(params)
    seasonalData.value = res.data
  } catch (e) { seasonalData.value = null; showError(e) }
  finally { loading.value = false }
}

function renderTrendChart() {
  if (!trendChartEl.value || !trendData.value?.daily?.length) return
  nextTick(() => {
    if (!trendChart) trendChart = echarts.init(trendChartEl.value)
    const dates = trendData.value.daily.map(d => d.date)
    const avgData = trendData.value.daily.map(d => d.avg_price)
    const maxData = trendData.value.daily.map(d => d.max_price)
    const minData = trendData.value.daily.map(d => d.min_price)
    const ma5Data = trendData.value.ma5 || []

    const series = [
      { name: '日均价', type: 'line', smooth: true, data: avgData, symbol: 'none', lineStyle: { width: 2.5, color: '#ff7b9c' } },
      { name: '最高价', type: 'line', smooth: true, data: maxData, symbol: 'none', lineStyle: { width: 1.5, color: '#c48bb8', type: 'dashed' } },
      { name: '最低价', type: 'line', smooth: true, data: minData, symbol: 'none', lineStyle: { width: 1.5, color: '#b09098', type: 'dashed' } },
    ]
    if (ma5Data.some(v => v !== null)) {
      series.push({ name: '5日移动平均', type: 'line', smooth: true, data: ma5Data, symbol: 'none', lineStyle: { width: 2, color: '#e8577a' } })
    }

    trendChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => { html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value != null ? Number(p.value).toFixed(2) : '-'} 元/MWh</b></div>` })
          return html
        }
      },
      legend: { data: series.map(s => s.name), textStyle: { color: '#b09098' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#b09098', fontSize: 10, rotate: 45 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: '元/MWh', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series,
      backgroundColor: 'transparent',
    })
    trendChart.resize()
  })
}

function renderComparisonChart() {
  if (!comparisonChartEl.value || !comparisonData.value?.nodes) return
  const nodeKeys = Object.keys(comparisonData.value.nodes)
  if (!nodeKeys.length) return
  nextTick(() => {
    if (!comparisonChart) comparisonChart = echarts.init(comparisonChartEl.value)
    const allDates = [...new Set(nodeKeys.flatMap(n => comparisonData.value.nodes[n].map(d => d.date)))].sort()
    const series = nodeKeys.map((node, i) => ({
      name: node,
      type: 'line',
      smooth: true,
      data: comparisonData.value.nodes[node].map(d => d.avg_price),
      symbol: 'none',
      lineStyle: { width: 2 },
    }))
    comparisonChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => { html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${Number(p.value).toFixed(2)} 元/MWh</b></div>` })
          return html
        }
      },
      legend: { data: series.map(s => s.name), textStyle: { color: '#b09098' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: allDates, axisLabel: { color: '#b09098', fontSize: 10, rotate: 45 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: '元/MWh', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series,
      backgroundColor: 'transparent',
    })
    comparisonChart.resize()
  })
}

function renderSpotChart() {
  if (!spotChartEl.value || !spotData.value?.items?.length) return
  nextTick(() => {
    if (!spotChart) spotChart = echarts.init(spotChartEl.value)
    const months = [...new Set(spotData.value.items.map(d => d.trade_month))].sort()
    const types = [...new Set(spotData.value.items.map(d => d.trade_type))]
    const series = types.map(type => ({
      name: type,
      type: 'line',
      smooth: true,
      data: months.map(m => {
        const found = spotData.value.items.find(d => d.trade_month === m && d.trade_type === type)
        return found ? found.avg_price : null
      }),
      symbol: 'none',
      lineStyle: { width: 2 },
    }))
    spotChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => { html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value != null ? Number(p.value).toFixed(2) : '-'} 元/MWh</b></div>` })
          return html
        }
      },
      legend: { data: series.map(s => s.name), textStyle: { color: '#b09098' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: months, axisLabel: { color: '#b09098', fontSize: 10 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: '元/MWh', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series,
      backgroundColor: 'transparent',
    })
    spotChart.resize()
  })
}

function renderVolatilityChart() {
  if (!volatilityChartEl.value || !volatilityData.value?.daily?.length) return
  nextTick(() => {
    if (!volatilityChart) volatilityChart = echarts.init(volatilityChartEl.value)

    const dates = volatilityData.value.daily.map(d => d.date)
    const avgData = volatilityData.value.daily.map(d => d.avg_price)
    const stdData = volatilityData.value.daily.map(d => d.std_dev)
    const cvData = volatilityData.value.daily.map(d => (d.cv * 100).toFixed(2))

    volatilityChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => { html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value != null ? Number(p.value).toFixed(2) : '-'}</b></div>` })
          return html
        }
      },
      legend: { data: ['日均价', '标准差', '变异系数(%)'], textStyle: { color: '#b09098' }, bottom: 0 },
      grid: { left: 60, right: 60, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#b09098', fontSize: 10, rotate: 45 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: [
        { type: 'value', name: '元/MWh', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
        { type: 'value', name: '%', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { show: false } },
      ],
      series: [
        { name: '日均价', type: 'line', smooth: true, data: avgData, symbol: 'none', lineStyle: { width: 2.5, color: '#ff7b9c' }, yAxisIndex: 0 },
        { name: '标准差', type: 'line', smooth: true, data: stdData, symbol: 'none', lineStyle: { width: 1.5, color: '#c48bb8', type: 'dashed' }, yAxisIndex: 0 },
        { name: '变异系数(%)', type: 'bar', data: cvData, itemStyle: { color: 'rgba(255,123,156,0.3)' }, yAxisIndex: 1, barWidth: '60%' },
      ],
      backgroundColor: 'transparent',
    })
    volatilityChart.resize()
  })
}

function renderSeasonalChart() {
  if (!seasonalChartEl.value || !seasonalData.value?.monthly?.length) return
  nextTick(() => {
    if (!seasonalChart) seasonalChart = echarts.init(seasonalChartEl.value)
    const months = seasonalData.value.monthly.map(d => d.month)
    const avgData = seasonalData.value.monthly.map(d => d.avg_price)
    const maxData = seasonalData.value.monthly.map(d => d.max_price)
    const minData = seasonalData.value.monthly.map(d => d.min_price)

    seasonalChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => { html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value != null ? Number(p.value).toFixed(2) : '-'} 元/MWh</b></div>` })
          return html
        }
      },
      legend: { data: ['月均价', '月最高', '月最低'], textStyle: { color: '#b09098' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: months, axisLabel: { color: '#b09098', fontSize: 10, rotate: 45 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: '元/MWh', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series: [
        { name: '月均价', type: 'line', smooth: true, data: avgData, symbol: 'none', lineStyle: { width: 2.5, color: '#ff7b9c' }, areaStyle: { opacity: 0.08 } },
        { name: '月最高', type: 'line', smooth: true, data: maxData, symbol: 'none', lineStyle: { width: 1.5, color: '#c48bb8', type: 'dashed' } },
        { name: '月最低', type: 'line', smooth: true, data: minData, symbol: 'none', lineStyle: { width: 1.5, color: '#b09098', type: 'dashed' } },
      ],
      backgroundColor: 'transparent',
    })
    seasonalChart.resize()
  })
}

watch(trendData, renderTrendChart, { deep: true })
watch(comparisonData, renderComparisonChart, { deep: true })
watch(spotData, renderSpotChart, { deep: true })
watch(volatilityData, renderVolatilityChart, { deep: true })
watch(seasonalData, renderSeasonalChart, { deep: true })

async function search() {
  if (tab.value === 'trend') await loadTrend()
  else if (tab.value === 'comparison') await loadComparison()
  else if (tab.value === 'spot') await loadSpot()
  else if (tab.value === 'volatility') await loadVolatility()
  else await loadSeasonal()
}

function switchTab(t) {
  tab.value = t
  if (t === 'trend') loadTrend()
  else if (t === 'comparison') loadComparison()
  else if (t === 'spot') loadSpot()
  else if (t === 'volatility') loadVolatility()
  else loadSeasonal()
}
</script>

<template>
  <div class="pt-root">
    <div class="tabs">
      <button :class="{ on: tab === 'trend' }" @click="switchTab('trend')">日趋势</button>
      <button :class="{ on: tab === 'comparison' }" @click="switchTab('comparison')">节点对比</button>
      <button :class="{ on: tab === 'volatility' }" @click="switchTab('volatility')">波动率</button>
      <button :class="{ on: tab === 'seasonal' }" @click="switchTab('seasonal')">季节性</button>
      <button :class="{ on: tab === 'spot' }" @click="switchTab('spot')">现货趋势</button>
    </div>

    <div v-if="tab === 'trend'" class="filter-bar">
      <label>起始 <input v-model="dateFrom" type="date" /></label>
      <label>结束 <input v-model="dateTo" type="date" /></label>
      <label>节点 <input v-model="nodeName" placeholder="可选" /></label>
      <label>类型 <input v-model="priceType" placeholder="可选" /></label>
      <button class="btn btn-primary" @click="search">查询</button>
    </div>

    <div v-if="tab === 'comparison'" class="filter-bar">
      <label>起始 <input v-model="dateFrom" type="date" /></label>
      <label>结束 <input v-model="dateTo" type="date" /></label>
      <label>节点 <input v-model="nodesText" placeholder="逗号分隔，如 节点A,节点B" style="min-width:200px" /></label>
      <button class="btn btn-primary" @click="search">对比</button>
    </div>

    <div v-if="tab === 'volatility'" class="filter-bar">
      <label>起始 <input v-model="dateFrom" type="date" /></label>
      <label>结束 <input v-model="dateTo" type="date" /></label>
      <label>节点 <input v-model="nodeName" placeholder="可选" /></label>
      <label>类型 <input v-model="priceType" placeholder="可选" /></label>
      <button class="btn btn-primary" @click="search">分析</button>
    </div>

    <div v-if="tab === 'seasonal'" class="filter-bar">
      <label>年份 <input v-model="seasonalYear" type="number" placeholder="如 2026" style="width:100px" /></label>
      <label>节点 <input v-model="seasonalNode" placeholder="可选" /></label>
      <button class="btn btn-primary" @click="search">查询</button>
    </div>

    <div v-if="tab === 'spot'" class="filter-bar">
      <label>交易类型 <input v-model="tradeType" placeholder="可选，如 日前" /></label>
      <button class="btn btn-primary" @click="search">查询</button>
      <span v-if="spotData?.available_types?.length" class="hint">可选类型: {{ spotData.available_types.join(', ') }}</span>
    </div>

    <div v-if="tab === 'trend'" class="chart-wrap">
      <h3 class="section-title">价格趋势</h3>
      <div v-if="!trendData?.daily?.length && !loading" class="chart-empty">请选择日期范围后查询</div>
      <div ref="trendChartEl" class="chart-el" v-show="trendData?.daily?.length"></div>
    </div>

    <div v-if="tab === 'comparison'" class="chart-wrap">
      <h3 class="section-title">多节点价格对比</h3>
      <div v-if="!comparisonData?.nodes || !Object.keys(comparisonData.nodes).length && !loading" class="chart-empty">请选择日期范围后查询</div>
      <div ref="comparisonChartEl" class="chart-el" v-show="comparisonData?.nodes && Object.keys(comparisonData.nodes).length"></div>
    </div>

    <div v-if="tab === 'volatility'" class="volatility-result">
      <div class="chart-wrap">
        <h3 class="section-title">价格波动率分析</h3>
        <div v-if="!volatilityData?.daily?.length && !loading" class="chart-empty">请选择日期范围后查询</div>
        <div ref="volatilityChartEl" class="chart-el" v-show="volatilityData?.daily?.length"></div>
      </div>

      <div class="stats-grid" v-if="volatilityData?.overall">
        <div class="stat-card">
          <span class="stat-label">整体均价</span>
          <span class="stat-val">{{ volatilityData.overall.avg_price }} 元/MWh</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">整体标准差</span>
          <span class="stat-val">{{ volatilityData.overall.std_dev }} 元/MWh</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">整体变异系数</span>
          <span class="stat-val">{{ (volatilityData.overall.cv * 100).toFixed(2) }}%</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">价格区间</span>
          <span class="stat-val">{{ volatilityData.overall.min }} ~ {{ volatilityData.overall.max }} 元/MWh</span>
        </div>
      </div>
    </div>

    <div v-if="tab === 'seasonal'" class="chart-wrap">
      <h3 class="section-title">季节性价格趋势</h3>
      <div v-if="!seasonalData?.monthly?.length && !loading" class="chart-empty">请选择年份后查询</div>
      <div ref="seasonalChartEl" class="chart-el" v-show="seasonalData?.monthly?.length"></div>

      <div class="month-grid" v-if="seasonalData?.by_month">
        <h4 class="section-title" style="margin-top:20px">各月分布</h4>
        <div v-for="(items, m) in seasonalData.by_month" :key="m" class="month-group">
          <div class="month-label">{{ m }}月</div>
          <div v-for="item in items" :key="item.month" class="month-item">
            <span class="mi-date">{{ item.month }}</span>
            <span class="mi-val">{{ item.avg_price }} 元/MWh</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="tab === 'spot'" class="chart-wrap">
      <h3 class="section-title">现货市场价格趋势</h3>
      <div v-if="!spotData?.items?.length && !loading" class="chart-empty">暂无数据</div>
      <div ref="spotChartEl" class="chart-el" v-show="spotData?.items?.length"></div>
    </div>
  </div>
</template>

<style scoped>
.pt-root { display: flex; flex-direction: column; gap: 24px; }

.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.filter-bar label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--t3); }
.filter-bar input, .filter-bar select {
  padding: 8px 12px; background: rgba(255,105,135,.04); border: 1px solid var(--border);
  border-radius: 8px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px; width: auto;
}
.hint { font-size: 12px; color: var(--t3); }

.section-title { font-family: 'Cormorant Garamond', serif; font-size: 1.2rem; font-weight: 400; margin-bottom: 12px; color: var(--t1); }

.chart-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
.chart-el { height: 360px; }
.chart-empty { height: 360px; display: flex; align-items: center; justify-content: center; color: var(--t3); font-weight: 300; }

.volatility-result { display: flex; flex-direction: column; gap: 20px; }

.stats-grid { display: flex; gap: 16px; flex-wrap: wrap; }
.stat-card {
  flex: 1; min-width: 180px; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r); padding: 20px 24px; display: flex; flex-direction: column; gap: 6px;
}
.stat-label { font-size: 12px; color: var(--t3); }
.stat-val { font-size: 1.2rem; font-weight: 500; color: var(--cyan); font-family: 'Cormorant Garamond', serif; }

.month-grid { display: flex; flex-direction: column; gap: 12px; }
.month-group { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.month-label { font-size: 13px; font-weight: 500; color: var(--t2); min-width: 40px; }
.month-item { display: flex; align-items: center; gap: 8px; padding: 4px 10px; background: rgba(255,123,156,.04); border: 1px solid rgba(255,123,156,.1); border-radius: 6px; }
.mi-date { font-size: 11px; color: var(--t3); }
.mi-val { font-size: 12px; font-weight: 500; color: var(--cyan); }
</style>

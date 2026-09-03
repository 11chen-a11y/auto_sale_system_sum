<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getHistory, getPredict, getPredictWeather } from '../api/loadForecast'
import { showError } from '../utils/error'
import WeatherManage from './Weather.vue'

const tab = ref('history')
const dateFrom = ref('')
const dateTo = ref('')
const targetDate = ref('')
const lookbackWeeks = ref(4)
const sigma = ref(5)
const historyData = ref([])
const predictData = ref(null)
const weatherPredictData = ref(null)
const loading = ref(false)
const historyChartEl = ref(null)
const predictChartEl = ref(null)
const weatherChartEl = ref(null)
let historyChart = null
let predictChart = null
let weatherChart = null

function today() { return new Date().toISOString().slice(0, 10) }

onMounted(() => {
  const d = today()
  dateTo.value = d
  const past = new Date()
  past.setDate(past.getDate() - 30)
  dateFrom.value = past.toISOString().slice(0, 10)
  targetDate.value = d
  loadHistory()
})

function timeLabels() {
  const labels = []
  for (let i = 0; i < 96; i++) {
    const h = String(Math.floor(i / 4)).padStart(2, '0')
    const m = String((i % 4) * 15).padStart(2, '0')
    labels.push(`${h}:${m}`)
  }
  return labels
}

async function loadHistory() {
  if (!dateFrom.value || !dateTo.value) return
  loading.value = true
  try {
    const res = await getHistory({ date_from: dateFrom.value, date_to: dateTo.value })
    historyData.value = res.data.days || []
  } catch (e) { historyData.value = []; showError(e) }
  finally { loading.value = false }
}

async function loadPredict() {
  if (!targetDate.value) return
  loading.value = true
  try {
    const res = await getPredict({ target_date: targetDate.value, lookback_weeks: lookbackWeeks.value })
    predictData.value = res.data
  } catch (e) { predictData.value = null; showError(e) }
  finally { loading.value = false }
}

async function loadWeatherPredict() {
  if (!targetDate.value) return
  loading.value = true
  try {
    const res = await getPredictWeather({
      target_date: targetDate.value,
      lookback_weeks: lookbackWeeks.value,
      sigma: sigma.value,
    })
    weatherPredictData.value = res.data
  } catch (e) { weatherPredictData.value = null; showError(e) }
  finally { loading.value = false }
}

function renderHistoryChart() {
  if (!historyChartEl.value || !historyData.value.length) return
  nextTick(() => {
    if (!historyChart) historyChart = echarts.init(historyChartEl.value)
    const labels = timeLabels()
    const series = historyData.value.map((d, i) => ({
      name: d.date,
      type: 'line',
      smooth: true,
      data: d.slots ? Object.values(d.slots) : [],
      symbol: 'none',
      lineStyle: { width: 1.5 },
      areaStyle: i === historyData.value.length - 1 ? { opacity: 0.08 } : undefined,
    }))
    historyChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => { html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value} kWh</b></div>` })
          return html
        }
      },
      legend: { data: series.map(s => s.name), textStyle: { color: '#b09098' }, bottom: 0, type: 'scroll' },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#b09098', fontSize: 10, interval: 11 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: 'kWh', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series,
      backgroundColor: 'transparent',
    })
    historyChart.resize()
  })
}

function renderPredictChart() {
  if (!predictChartEl.value || !predictData.value || !predictData.value.predicted_slots) return
  nextTick(() => {
    if (!predictChart) predictChart = echarts.init(predictChartEl.value)
    const labels = timeLabels()
    const predVals = Object.values(predictData.value.predicted_slots)
    predictChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => { html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value} kWh</b></div>` })
          return html
        }
      },
      grid: { left: 60, right: 20, top: 20, bottom: 28 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#b09098', fontSize: 10, interval: 11 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: 'kWh', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series: [{
        name: `预测值 (${predictData.value.target_date})`,
        type: 'line',
        smooth: true,
        data: predVals,
        symbol: 'none',
        lineStyle: { width: 2, color: '#ff7b9c' },
        areaStyle: { opacity: 0.1, color: '#ff7b9c' },
      }],
      backgroundColor: 'transparent',
    })
    predictChart.resize()
  })
}

function renderWeatherChart() {
  if (!weatherChartEl.value || !weatherPredictData.value || !weatherPredictData.value.predicted_slots) return
  nextTick(() => {
    if (!weatherChart) weatherChart = echarts.init(weatherChartEl.value)
    const labels = timeLabels()
    const predVals = Object.values(weatherPredictData.value.predicted_slots)
    const lowerVals = Object.values(weatherPredictData.value.confidence_lower || {})
    const upperVals = Object.values(weatherPredictData.value.confidence_upper || {})

    weatherChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => {
            if (p.seriesName === '置信区间') return
            html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value != null ? Number(p.value).toFixed(2) : '-'} kWh</b></div>`
          })
          return html
        }
      },
      grid: { left: 60, right: 20, top: 20, bottom: 28 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#b09098', fontSize: 10, interval: 11 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: 'kWh', nameTextStyle: { color: '#b09098' }, axisLabel: { color: '#b09098' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series: [
        {
          name: '置信上界',
          type: 'line',
          smooth: true,
          data: upperVals,
          symbol: 'none',
          lineStyle: { width: 0 },
          silent: true,
        },
        {
          name: '置信区间',
          type: 'line',
          smooth: true,
          data: lowerVals,
          symbol: 'none',
          lineStyle: { width: 0 },
          areaStyle: { color: 'rgba(255,123,156,0.15)' },
          silent: true,
        },
        {
          name: `预测值 (${weatherPredictData.value.target_date})`,
          type: 'line',
          smooth: true,
          data: predVals,
          symbol: 'none',
          lineStyle: { width: 2.5, color: '#ff7b9c' },
        },
      ],
      backgroundColor: 'transparent',
    })
    weatherChart.resize()
  })
}

watch(historyData, renderHistoryChart, { deep: true })
watch(predictData, renderPredictChart, { deep: true })
watch(weatherPredictData, renderWeatherChart, { deep: true })

async function search() {
  if (tab.value === 'history') await loadHistory()
  else if (tab.value === 'predict') await loadPredict()
  else if (tab.value === 'weather') await loadWeatherPredict()
}

function switchTab(t) {
  tab.value = t
  if (t === 'history') loadHistory()
  else if (t === 'predict') loadPredict()
  else if (t === 'weather') loadWeatherPredict()
}
</script>

<template>
  <div class="lf-root">
    <div class="tabs">
      <button :class="{ on: tab === 'history' }" @click="switchTab('history')">历史负荷</button>
      <button :class="{ on: tab === 'predict' }" @click="switchTab('predict')">相似日预测</button>
      <button :class="{ on: tab === 'weather' }" @click="switchTab('weather')">天气加权预测</button>
      <button :class="{ on: tab === 'weatherData' }" @click="switchTab('weatherData')">天气数据</button>
    </div>

    <div v-if="tab === 'history'" class="filter-bar">
      <label>起始 <input v-model="dateFrom" type="date" /></label>
      <label>结束 <input v-model="dateTo" type="date" /></label>
      <button class="btn btn-primary" @click="search">查询</button>
    </div>

    <div v-if="tab === 'predict'" class="filter-bar">
      <label>目标日期 <input v-model="targetDate" type="date" /></label>
      <label>参考周数
        <select v-model.number="lookbackWeeks">
          <option :value="1">1周</option><option :value="2">2周</option><option :value="3">3周</option><option :value="4">4周</option><option :value="6">6周</option><option :value="8">8周</option>
        </select>
      </label>
      <button class="btn btn-primary" @click="search">预测</button>
    </div>

    <div v-if="tab === 'weather'" class="filter-bar">
      <label>目标日期 <input v-model="targetDate" type="date" /></label>
      <label>参考周数
        <select v-model.number="lookbackWeeks">
          <option :value="1">1周</option><option :value="2">2周</option><option :value="3">3周</option><option :value="4">4周</option><option :value="6">6周</option><option :value="8">8周</option>
        </select>
      </label>
      <label>温度敏感度
        <select v-model.number="sigma">
          <option :value="2">高敏感 (2°C)</option><option :value="5">中等 (5°C)</option><option :value="10">低敏感 (10°C)</option><option :value="15">极低 (15°C)</option>
        </select>
      </label>
      <button class="btn btn-primary" @click="search">预测</button>
    </div>

    <div v-if="tab === 'history'" class="chart-wrap">
      <h3 class="section-title">历史负荷曲线</h3>
      <div v-if="!historyData.length && !loading" class="chart-empty">请选择日期范围后查询</div>
      <div ref="historyChartEl" class="chart-el" v-show="historyData.length"></div>
    </div>

    <div v-if="tab === 'predict'" class="predict-result">
      <div class="chart-wrap">
        <h3 class="section-title">预测结果 — {{ predictData?.target_date || '-' }}</h3>
        <div v-if="!predictData" class="chart-empty">请选择目标日期并预测</div>
        <div v-else-if="!predictData.predicted_slots" class="chart-empty">{{ predictData.message }}</div>
        <div ref="predictChartEl" class="chart-el" v-show="predictData?.predicted_slots"></div>
      </div>
      <div class="info-cards" v-if="predictData?.predicted_slots">
        <div class="info-card">
          <span class="info-label">预测日总负荷</span>
          <span class="info-value">{{ (predictData.total_kwh || 0).toLocaleString() }} kWh</span>
        </div>
        <div class="info-card">
          <span class="info-label">参考周数</span>
          <span class="info-value">{{ predictData.lookback_weeks }} 周</span>
        </div>
        <div class="info-card">
          <span class="info-label">参考日期</span>
          <span class="info-value ref-dates">{{ predictData.reference_dates?.join('、') }}</span>
        </div>
      </div>
    </div>

    <div v-if="tab === 'weather'" class="predict-result">
      <div class="chart-wrap">
        <h3 class="section-title">天气加权预测 — {{ weatherPredictData?.target_date || '-' }}</h3>
        <div v-if="!weatherPredictData" class="chart-empty">请选择目标日期并预测</div>
        <div v-else-if="!weatherPredictData.predicted_slots" class="chart-empty">{{ weatherPredictData.message }}</div>
        <div ref="weatherChartEl" class="chart-el" v-show="weatherPredictData?.predicted_slots"></div>
      </div>
      <div class="info-cards" v-if="weatherPredictData?.predicted_slots">
        <div class="info-card">
          <span class="info-label">预测日总负荷</span>
          <span class="info-value">{{ (weatherPredictData.total_kwh || 0).toLocaleString() }} kWh</span>
        </div>
        <div class="info-card">
          <span class="info-label">目标日温度</span>
          <span class="info-value">{{ weatherPredictData.target_temperature ?? '未知' }} °C</span>
        </div>
        <div class="info-card">
          <span class="info-label">温度敏感度 (σ)</span>
          <span class="info-value">{{ weatherPredictData.sigma }} °C</span>
        </div>
      </div>
      <div class="weather-summary" v-if="weatherPredictData?.temperature_summary?.avg != null">
        <div class="info-card">
          <span class="info-label">参考日均温</span>
          <span class="info-value">{{ weatherPredictData.temperature_summary.avg }} °C</span>
        </div>
        <div class="info-card">
          <span class="info-label">参考日最低温</span>
          <span class="info-value">{{ weatherPredictData.temperature_summary.min }} °C</span>
        </div>
        <div class="info-card">
          <span class="info-label">参考日最高温</span>
          <span class="info-value">{{ weatherPredictData.temperature_summary.max }} °C</span>
        </div>
      </div>
      <div class="ref-temps" v-if="weatherPredictData?.reference_temperatures">
        <h4 class="section-title">参考日温度明细</h4>
        <div class="temp-grid">
          <div v-for="(temp, d) in weatherPredictData.reference_temperatures" :key="d" class="temp-chip">
            <span class="temp-date">{{ d }}</span>
            <span class="temp-val">{{ temp }}°C</span>
          </div>
        </div>
      </div>
    </div>

    <WeatherManage v-if="tab === 'weatherData'" />
  </div>
</template>

<style scoped>
.lf-root { display: flex; flex-direction: column; gap: 24px; }

.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.filter-bar label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--t3); }
.filter-bar input, .filter-bar select {
  padding: 8px 12px; background: rgba(255,105,135,.04); border: 1px solid var(--border);
  border-radius: 8px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px; width: auto;
}
.filter-bar select option { background: #fff5f7; }

.section-title { font-family: 'Cormorant Garamond', serif; font-size: 1.2rem; font-weight: 400; margin-bottom: 12px; color: var(--t1); }

.chart-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
.chart-el { height: 360px; }
.chart-empty { height: 360px; display: flex; align-items: center; justify-content: center; color: var(--t3); font-weight: 300; }

.predict-result { display: flex; flex-direction: column; gap: 20px; }

.info-cards, .weather-summary { display: flex; gap: 16px; flex-wrap: wrap; }
.info-card {
  flex: 1; min-width: 200px; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r); padding: 20px 24px; display: flex; flex-direction: column; gap: 6px;
}
.info-label { font-size: 12px; color: var(--t3); }
.info-value { font-size: 1.3rem; font-weight: 500; color: var(--cyan); font-family: 'Cormorant Garamond', serif; }
.ref-dates { font-size: 13px; font-family: 'Outfit', sans-serif; font-weight: 300; color: var(--t2); }

.ref-temps { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
.temp-grid { display: flex; gap: 8px; flex-wrap: wrap; }
.temp-chip {
  display: flex; align-items: center; gap: 8px; padding: 8px 14px;
  background: rgba(255,123,156,.06); border: 1px solid rgba(255,123,156,.15); border-radius: 8px;
}
.temp-date { font-size: 12px; color: var(--t3); }
.temp-val { font-size: 13px; font-weight: 500; color: var(--cyan); }
</style>

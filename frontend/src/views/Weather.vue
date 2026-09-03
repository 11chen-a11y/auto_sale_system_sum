<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { useUserStore } from '../stores/user'
import { getStations, getCities, getTypes, getDates, listRecords, getChartData, createRecord, updateRecord, deleteRecord, exportRecords } from '../api/weather'
import { showError } from '../utils/error'
import { saveBlob } from '../utils/download'

const store = useUserStore()
const isAdmin = computed(() => store.userInfo?.role === 'admin')

const stations = ref([])
const cities = ref([])
const types = ref([])
const dates = ref([])
const filters = ref({ station_name: '', city: '', data_type: '', date_from: '', date_to: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const chartData = ref([])
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const form = ref({ station_name: '', city: '', record_date: '', data_type: '', temperature: null })
const chartEl = ref(null)
let chart = null

async function initFilters() {
  const [s, c, t, d] = await Promise.all([getStations(), getCities(), getTypes(), getDates()])
  stations.value = s.data
  cities.value = c.data
  types.value = t.data
  dates.value = d.data
}

async function refreshStations() {
  const params = {}
  if (filters.value.city) params.city = filters.value.city
  const res = await getStations(params)
  stations.value = res.data
}

async function refreshCities() {
  const params = {}
  if (filters.value.station_name) params.station_name = filters.value.station_name
  const res = await getCities(params)
  cities.value = res.data
}

async function refreshTypes() {
  const params = {}
  if (filters.value.station_name) params.station_name = filters.value.station_name
  if (filters.value.city) params.city = filters.value.city
  const res = await getTypes(params)
  types.value = res.data
}

watch(() => filters.value.city, () => { refreshStations(); refreshTypes() })
watch(() => filters.value.station_name, () => { refreshCities(); refreshTypes() })

function renderChart() {
  if (!chartEl.value || !chartData.value.length) return
  nextTick(() => {
    if (!chart) chart = echarts.init(chartEl.value)
    const labels = chartData.value.map(r => r.record_date)
    const data = chartData.value.map(r => r.temperature)
    chart.setOption({
      tooltip: { trigger: 'axis', formatter: params => `${params[0].axisValue}<br/>温度: ${params[0].value}°C` },
      grid: { left: 50, right: 20, top: 20, bottom: 40 },
      xAxis: { type: 'category', data: labels, axisLabel: { color: '#8a8f98', fontSize: 10 }, axisLine: { lineStyle: { color: '#2a2d34' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: '°C', nameTextStyle: { color: '#8a8f98' }, axisLabel: { color: '#8a8f98' }, splitLine: { lineStyle: { color: '#2a2d34' } } },
      series: [{ type: 'line', smooth: true, data, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2 }, areaStyle: { opacity: 0.08 } }],
      backgroundColor: 'transparent',
    })
    chart.resize()
  })
}

watch(chartData, renderChart, { deep: true })

async function loadChart() {
  const dFrom = filters.value.date_from || dates.value[dates.value.length - 30] || ''
  const dTo = filters.value.date_to || dates.value[0] || ''
  if (!dFrom || !dTo) return
  try {
    const res = await getChartData({ date_from: dFrom, date_to: dTo, station_name: filters.value.station_name || undefined, city: filters.value.city || undefined })
    chartData.value = res.data
  } catch (e) { chartData.value = []; showError(e) }
}

async function loadTable() {
  loading.value = true
  try {
    const res = await listRecords({ page: page.value, page_size: pageSize.value, ...filters.value })
    records.value = res.data.items
    total.value = res.data.total
    page.value = res.data.page
  } catch (e) { showError(e) } finally { loading.value = false }
}

async function search() {
  page.value = 1
  await Promise.all([loadChart(), loadTable()])
}

async function doExport() {
  exporting.value = true
  try {
    const res = await exportRecords(filters.value)
    saveBlob(res, 'weather_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { station_name: '', city: '', record_date: '', data_type: '', temperature: null }
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.weather_id
  form.value = { station_name: row.station_name || '', city: row.city || '', record_date: row.record_date, data_type: row.data_type || '', temperature: row.temperature }
  showForm.value = true
}

async function submitForm() {
  if (editing.value) {
    await updateRecord(editing.value, form.value)
  } else {
    await createRecord(form.value)
  }
  showForm.value = false
  await Promise.all([search(), refreshStations(), refreshCities(), refreshTypes()])
}

async function removeRow(id) {
  if (!confirm('确认删除？')) return
  await deleteRecord(id)
  await Promise.all([search(), refreshStations(), refreshCities(), refreshTypes()])
}

onMounted(async () => {
  await initFilters()
  await search()
})
</script>

<template>
  <div class="we-root">
    <div class="filter-bar">
      <select v-model="filters.station_name">
        <option value="">全部站点</option>
        <option v-for="s in stations" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="filters.city">
        <option value="">全部城市</option>
        <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="filters.data_type">
        <option value="">全部类型</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <input v-model="filters.date_from" type="date" placeholder="起始日期" />
      <input v-model="filters.date_to" type="date" placeholder="结束日期" />
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button v-if="isAdmin" class="btn btn-ghost" @click="openCreate">+ 新增</button>
    </div>

    <div class="chart-wrap">
      <h3 class="section-title">温度趋势</h3>
      <div v-if="!chartData.length" class="chart-empty">请选择条件后查询</div>
      <div ref="chartEl" class="chart-el" v-show="chartData.length"></div>
    </div>

    <div class="table-wrap">
      <h3 class="section-title">天气记录</h3>
      <table>
        <thead>
          <tr>
            <th>日期</th><th>站点</th><th>城市</th><th>数据类型</th><th>温度 (°C)</th><th v-if="isAdmin">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.weather_id">
            <td>{{ r.record_date }}</td>
            <td>{{ r.station_name || '-' }}</td>
            <td>{{ r.city || '-' }}</td>
            <td><span class="tag">{{ r.data_type || '-' }}</span></td>
            <td>{{ r.temperature != null ? Number(r.temperature).toFixed(1) : '-' }}</td>
            <td v-if="isAdmin">
              <button class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.weather_id)">删除</button>
            </td>
          </tr>
          <tr v-if="!records.length">
            <td :colspan="isAdmin ? 6 : 5" class="empty">暂无数据</td>
          </tr>
        </tbody>
      </table>
      <div class="pagination" v-if="total > pageSize">
        <span>共 {{ total }} 条</span>
        <button :disabled="page <= 1" @click="page--; loadTable()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button :disabled="page >= Math.ceil(total / pageSize)" @click="page++; loadTable()">下一页</button>
      </div>
    </div>

    <div class="modal-overlay" v-if="showForm" @click.self="showForm = false">
      <div class="modal">
        <h3>{{ editing ? '编辑' : '新增' }}天气记录</h3>
        <div class="modal-body">
          <label>站点 <input v-model="form.station_name" :disabled="!!editing" /></label>
          <label>城市 <input v-model="form.city" /></label>
          <label>日期 <input v-model="form.record_date" type="date" :disabled="!!editing" /></label>
          <label>数据类型
            <select v-model="form.data_type">
              <option value="">-</option>
              <option value="日均温">日均温</option>
              <option value="最高温">最高温</option>
              <option value="最低温">最低温</option>
              <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
            </select>
          </label>
          <label>温度 (°C) <input v-model="form.temperature" type="number" step="0.1" /></label>
        </div>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="showForm = false">取消</button>
          <button class="btn btn-primary" @click="submitForm">{{ editing ? '保存' : '创建' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.we-root { display: flex; flex-direction: column; gap: 24px; }

.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.filter-bar select, .filter-bar input {
  padding: 8px 12px; background: rgba(255,255,255,.03); border: 1px solid var(--border);
  border-radius: 8px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.filter-bar select option { background: #1a1d24; }

.section-title { font-family: 'Cormorant Garamond', serif; font-size: 1.2rem; font-weight: 400; margin-bottom: 12px; color: var(--t1); }

.chart-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
.chart-el { height: 320px; }
.chart-empty { height: 320px; display: flex; align-items: center; justify-content: center; color: var(--t3); font-weight: 300; }

.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 600; letter-spacing: .08em; color: var(--t3); border-bottom: 1px solid var(--border); }
td { padding: 10px 12px; font-size: 13px; color: var(--t2); border-bottom: 1px solid rgba(255,255,255,.03); }
tr:hover td { background: rgba(255,255,255,.02); }
.tag { display: inline-block; padding: 2px 10px; background: rgba(0,212,170,.08); border-radius: 100px; font-size: 11px; color: var(--cyan); }
.empty { text-align: center; color: var(--t3); padding: 32px !important; }
.danger { color: #ff6b6b !important; }
.danger:hover { background: rgba(255,107,107,.1) !important; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 16px; font-size: 13px; color: var(--t3); }
.pagination button { padding: 6px 14px; background: rgba(255,255,255,.03); border: 1px solid var(--border); border-radius: 6px; color: var(--t2); cursor: pointer; }
.pagination button:disabled { opacity: .3; cursor: default; }
.pagination button:hover:not(:disabled) { background: rgba(255,255,255,.06); }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal { background: #1a1d24; border: 1px solid var(--border); border-radius: var(--r); padding: 28px; min-width: 420px; max-width: 520px; }
.modal h3 { font-family: 'Cormorant Garamond', serif; font-size: 1.3rem; margin-bottom: 20px; }
.modal-body { display: flex; flex-direction: column; gap: 14px; }
.modal-body label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--t3); }
.modal-body input, .modal-body select, .modal-body textarea {
  padding: 8px 10px; background: rgba(255,255,255,.03); border: 1px solid var(--border);
  border-radius: 6px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.modal-body select option { background: #1a1d24; }
.modal-body textarea { resize: vertical; font-family: 'Courier New', monospace; font-size: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
</style>

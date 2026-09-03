<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { getStations, getEnergyTypes, getDates, listRecords, getChartData, createRecord, updateRecord, deleteRecord, exportRecords } from '../api/newEnergy'
import { showError } from '../utils/error'
import { saveBlob } from '../utils/download'

const stations = ref([])
const types = ref([])
const dates = ref([])
const filters = ref({ record_date: '', station_name: '', energy_type: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const chartData = ref([])
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const form = ref({ record_date: '', station_name: '', energy_type: '' })
const forecastSlotsText = ref('')
const actualSlotsText = ref('')
const chartEl = ref(null)
const chartMode = ref('both')
let chart = null

async function initFilters() {
  const [s, t, d] = await Promise.all([getStations(), getEnergyTypes(), getDates()])
  stations.value = s.data
  types.value = t.data
  dates.value = d.data
  if (dates.value.length) filters.value.record_date = dates.value[0]
}

function timeLabels() {
  const labels = []
  for (let i = 0; i < 96; i++) {
    const h = String(Math.floor(i / 4)).padStart(2, '0')
    const m = String((i % 4) * 15).padStart(2, '0')
    labels.push(`${h}:${m}`)
  }
  return labels
}

function renderChart() {
  if (!chartEl.value) return
  nextTick(() => {
    if (!chart) chart = echarts.init(chartEl.value)
    const labels = timeLabels()
    const series = []

    chartData.value.forEach(item => {
      if (item.forecast_slots && chartMode.value !== 'actual') {
        series.push({
          name: `${item.station_name} 预测`,
          type: 'line',
          smooth: true,
          data: Object.values(item.forecast_slots),
          symbol: 'none',
          lineStyle: { width: 2, type: 'dashed' },
        })
      }
      if (item.actual_slots && chartMode.value !== 'forecast') {
        series.push({
          name: `${item.station_name} 实际`,
          type: 'line',
          smooth: true,
          data: Object.values(item.actual_slots),
          symbol: 'none',
          lineStyle: { width: 2 },
        })
      }
    })

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => {
            html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value} MW</b></div>`
          })
          return html
        }
      },
      legend: { data: series.map(s => s.name), textStyle: { color: '#a38990' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#a38990', fontSize: 10, interval: 11 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: 'MW', nameTextStyle: { color: '#a38990' }, axisLabel: { color: '#a38990' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series,
      backgroundColor: 'transparent',
    })
    chart.resize()
  })
}

watch(chartData, renderChart, { deep: true })

async function loadChart() {
  if (!filters.value.record_date) return
  try {
    const res = await getChartData({
      record_date: filters.value.record_date,
      station_name: filters.value.station_name || undefined,
      energy_type: filters.value.energy_type || undefined,
    })
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
    saveBlob(res, 'new_energy_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { record_date: '', station_name: '', energy_type: '' }
  forecastSlotsText.value = ''
  actualSlotsText.value = ''
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.energy_id
  form.value = { record_date: row.record_date, station_name: row.station_name, energy_type: row.energy_type || '' }
  forecastSlotsText.value = row.forecast_slots ? JSON.stringify(row.forecast_slots) : ''
  actualSlotsText.value = row.actual_slots ? JSON.stringify(row.actual_slots) : ''
  showForm.value = true
}

async function submitForm() {
  let forecast_slots = null
  let actual_slots = null
  if (forecastSlotsText.value.trim()) {
    try { forecast_slots = JSON.parse(forecastSlotsText.value) } catch { alert('预测数据格式错误'); return }
  }
  if (actualSlotsText.value.trim()) {
    try { actual_slots = JSON.parse(actualSlotsText.value) } catch { alert('实际数据格式错误'); return }
  }
  const payload = { ...form.value, forecast_slots, actual_slots }
  if (editing.value) {
    await updateRecord(editing.value, payload)
  } else {
    await createRecord(payload)
  }
  showForm.value = false
  await search()
}

async function removeRow(id) {
  if (!confirm('确认删除？')) return
  await deleteRecord(id)
  await search()
}

function parseSlotsPreview(slots) {
  if (!slots || typeof slots !== 'object') return '-'
  const vals = Object.values(slots).filter(v => v != null)
  if (!vals.length) return '-'
  const avg = (vals.reduce((a, b) => a + Number(b), 0) / vals.length).toFixed(2)
  const max = Math.max(...vals.map(Number)).toFixed(2)
  const min = Math.min(...vals.map(Number)).toFixed(2)
  const sum = vals.reduce((a, b) => a + Number(b), 0).toFixed(2)
  return `总量 ${sum} · 均 ${avg} · 峰 ${max} · 谷 ${min}`
}

function energyColor(type) {
  const map = { '风电': '#4fc3f7', '光伏': '#ffd54f', '水电': '#4db6ac', '火电': '#ff8a65' }
  return map[type] || '#81d4fa'
}

onMounted(async () => {
  await initFilters()
  await search()
})
</script>

<template>
  <div class="ne-root">
    <div class="filter-bar">
      <select v-model="filters.record_date">
        <option value="">全部日期</option>
        <option v-for="d in dates" :key="d" :value="d">{{ d }}</option>
      </select>
      <select v-model="filters.station_name">
        <option value="">全部场站</option>
        <option v-for="s in stations" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="filters.energy_type">
        <option value="">全部类型</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button class="btn btn-ghost" @click="openCreate">+ 新增</button>
    </div>

    <div class="chart-wrap">
      <div class="chart-header">
        <h3 class="section-title">出力曲线</h3>
        <div class="chart-mode">
          <label><input type="radio" v-model="chartMode" value="both" /> 预测+实际</label>
          <label><input type="radio" v-model="chartMode" value="forecast" /> 仅预测</label>
          <label><input type="radio" v-model="chartMode" value="actual" /> 仅实际</label>
        </div>
      </div>
      <div v-if="!chartData.length" class="chart-empty">请选择日期后查询</div>
      <div ref="chartEl" class="chart-el" v-show="chartData.length"></div>
    </div>

    <div class="table-wrap">
      <h3 class="section-title">出力记录</h3>
      <table>
        <thead>
          <tr>
            <th>日期</th><th>场站</th><th>类型</th><th>预测出力</th><th>实际出力</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.energy_id">
            <td>{{ r.record_date }}</td>
            <td>{{ r.station_name }}</td>
            <td><span class="tag" :style="{ background: energyColor(r.energy_type) + '22', color: energyColor(r.energy_type) }">{{ r.energy_type || '-' }}</span></td>
            <td class="slots-preview">{{ parseSlotsPreview(r.forecast_slots) }}</td>
            <td class="slots-preview">{{ parseSlotsPreview(r.actual_slots) }}</td>
            <td>
              <button class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.energy_id)">删除</button>
            </td>
          </tr>
          <tr v-if="!records.length">
            <td colspan="6" class="empty">暂无数据</td>
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
        <h3>{{ editing ? '编辑' : '新增' }}出力记录</h3>
        <div class="modal-body">
          <label>日期 <input v-model="form.record_date" type="date" :disabled="!!editing" /></label>
          <label>场站名称 <input v-model="form.station_name" :disabled="!!editing" /></label>
          <label>能源类型
            <select v-model="form.energy_type">
              <option value="">-</option>
              <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
              <option value="风电">风电</option>
              <option value="光伏">光伏</option>
              <option value="水电">水电</option>
            </select>
          </label>
          <label>预测出力 (JSON) <textarea v-model="forecastSlotsText" rows="4" placeholder='{"0":120.5,"1":115.2,...}'></textarea></label>
          <label>实际出力 (JSON) <textarea v-model="actualSlotsText" rows="4" placeholder='{"0":125.8,"1":118.3,...}'></textarea></label>
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
.ne-root { display: flex; flex-direction: column; gap: 24px; }

.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.filter-bar select, .filter-bar input {
  padding: 8px 12px; background: rgba(255,105,135,.04); border: 1px solid var(--border);
  border-radius: 8px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.filter-bar select option { background: #fff5f7; }

.section-title { font-family: 'Cormorant Garamond', serif; font-size: 1.2rem; font-weight: 400; margin-bottom: 12px; color: var(--t1); }

.chart-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
.chart-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 8px; }
.chart-mode { display: flex; gap: 16px; font-size: 12px; color: var(--t3); }
.chart-mode label { display: flex; align-items: center; gap: 4px; cursor: pointer; }
.chart-mode input { accent-color: var(--cyan); }
.chart-el { height: 360px; }
.chart-empty { height: 360px; display: flex; align-items: center; justify-content: center; color: var(--t3); font-weight: 300; }

.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 600; letter-spacing: .08em; color: var(--t3); border-bottom: 1px solid var(--border); }
td { padding: 10px 12px; font-size: 13px; color: var(--t2); border-bottom: 1px solid rgba(255,255,255,.03); }
tr:hover td { background: rgba(255,255,255,.02); }
.slots-preview { font-size: 12px; color: var(--t3); max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tag { display: inline-block; padding: 2px 10px; border-radius: 100px; font-size: 11px; }
.empty { text-align: center; color: var(--t3); padding: 32px !important; }
.danger { color: var(--danger) !important; }
.danger:hover { background: rgba(255,77,106,.1) !important; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 16px; font-size: 13px; color: var(--t3); }
.pagination button { padding: 6px 14px; background: rgba(255,255,255,.03); border: 1px solid var(--border); border-radius: 6px; color: var(--t2); cursor: pointer; }
.pagination button:disabled { opacity: .3; cursor: default; }
.pagination button:hover:not(:disabled) { background: rgba(255,255,255,.06); }

.modal-overlay { position: fixed; inset: 0; background: rgba(80,40,50,.35); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal { background: #fff; border: 1px solid var(--border); border-radius: var(--r); padding: 28px; min-width: 420px; max-width: 540px; }
.modal h3 { font-family: 'Cormorant Garamond', serif; font-size: 1.3rem; margin-bottom: 20px; }
.modal-body { display: flex; flex-direction: column; gap: 14px; }
.modal-body label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--t3); }
.modal-body input, .modal-body select, .modal-body textarea {
  padding: 8px 10px; background: rgba(255,255,255,.03); border: 1px solid var(--border);
  border-radius: 6px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.modal-body select option { background: #fff5f7; }
.modal-body textarea { resize: vertical; font-family: 'Courier New', monospace; font-size: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
</style>

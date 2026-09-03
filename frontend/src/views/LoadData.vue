<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { useUserStore } from '../stores/user'
import { getTypes, getDates, listRecords, getChartData, createRecord, updateRecord, deleteRecord, exportRecords } from '../api/loadData'
import { showError } from '../utils/error'
import { saveBlob } from '../utils/download'

const store = useUserStore()
const isAdmin = computed(() => store.userInfo?.role === 'admin')

const types = ref([])
const dates = ref([])
const filters = ref({ record_date: '', data_type: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const chartData = ref([])
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const form = ref({ record_date: '', data_type: '实际负荷', total_kwh: null, remarks: '' })
const slotsText = ref('')
const chartEl = ref(null)
let chart = null

async function initFilters() {
  const [t, d] = await Promise.all([getTypes(), getDates()])
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
    const series = chartData.value.map(item => ({
      name: `${item.data_type}`,
      type: 'line',
      smooth: true,
      data: item.slots ? Object.values(item.slots) : [],
      symbol: 'none',
      lineStyle: { width: 2 },
      areaStyle: { opacity: 0.08 },
    }))
    chart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
          params.forEach(p => {
            html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value} kW</b></div>`
          })
          return html
        }
      },
      legend: { data: series.map(s => s.name), textStyle: { color: '#8a8f98' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#8a8f98', fontSize: 10, interval: 11 }, axisLine: { lineStyle: { color: '#2a2d34' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: 'kW', nameTextStyle: { color: '#8a8f98' }, axisLabel: { color: '#8a8f98' }, splitLine: { lineStyle: { color: '#2a2d34' } } },
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
      data_type: filters.value.data_type || undefined,
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
    saveBlob(res, 'load_data_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { record_date: '', data_type: '实际负荷', total_kwh: null, remarks: '' }
  slotsText.value = ''
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.load_id
  form.value = { record_date: row.record_date, data_type: row.data_type || '', total_kwh: row.total_kwh, remarks: row.remarks || '' }
  slotsText.value = row.slots ? JSON.stringify(row.slots) : ''
  showForm.value = true
}

async function submitForm() {
  let slots = null
  if (slotsText.value.trim()) {
    try { slots = JSON.parse(slotsText.value) } catch { alert('slots 格式错误，请输入合法 JSON'); return }
  }
  const payload = { ...form.value, slots }
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

onMounted(async () => {
  await initFilters()
  await search()
})
</script>

<template>
  <div class="ld-root">
    <div class="filter-bar">
      <select v-model="filters.record_date">
        <option value="">全部日期</option>
        <option v-for="d in dates" :key="d" :value="d">{{ d }}</option>
      </select>
      <select v-model="filters.data_type">
        <option value="">全部类型</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button v-if="isAdmin" class="btn btn-ghost" @click="openCreate">+ 新增</button>
    </div>

    <div class="chart-wrap">
      <h3 class="section-title">日内负荷曲线</h3>
      <div v-if="!chartData.length" class="chart-empty">请选择日期后查询</div>
      <div ref="chartEl" class="chart-el" v-show="chartData.length"></div>
    </div>

    <div class="table-wrap">
      <h3 class="section-title">负荷记录</h3>
      <table>
        <thead>
          <tr>
            <th>日期</th><th>类型</th><th>日总电量</th><th>96点概览</th><th>备注</th><th v-if="isAdmin">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.load_id">
            <td>{{ r.record_date }}</td>
            <td><span class="tag">{{ r.data_type }}</span></td>
            <td>{{ r.total_kwh != null ? Number(r.total_kwh).toLocaleString() + ' kWh' : '-' }}</td>
            <td class="slots-preview">{{ parseSlotsPreview(r.slots) }}</td>
            <td class="slots-preview">{{ r.remarks || '-' }}</td>
            <td v-if="isAdmin">
              <button class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.load_id)">删除</button>
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
        <h3>{{ editing ? '编辑' : '新增' }}负荷记录</h3>
        <div class="modal-body">
          <label>日期 <input v-model="form.record_date" type="date" :disabled="!!editing" /></label>
          <label>数据类型
            <select v-model="form.data_type">
              <option value="实际负荷">实际负荷</option>
              <option value="预测负荷">预测负荷</option>
              <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
            </select>
          </label>
          <label>日总电量 (kWh) <input v-model="form.total_kwh" type="number" step="0.01" /></label>
          <label>96点数据 (JSON) <textarea v-model="slotsText" rows="4" placeholder='{"0":320.5,"1":315.2,...}'></textarea></label>
          <label>备注 <textarea v-model="form.remarks" rows="2"></textarea></label>
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
.ld-root { display: flex; flex-direction: column; gap: 24px; }

.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.filter-bar select, .filter-bar input {
  padding: 8px 12px; background: rgba(255,255,255,.03); border: 1px solid var(--border);
  border-radius: 8px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.filter-bar select option { background: #1a1d24; }

.section-title { font-family: 'Cormorant Garamond', serif; font-size: 1.2rem; font-weight: 400; margin-bottom: 12px; color: var(--t1); }

.chart-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
.chart-el { height: 360px; }
.chart-empty { height: 360px; display: flex; align-items: center; justify-content: center; color: var(--t3); font-weight: 300; }

.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 600; letter-spacing: .08em; color: var(--t3); border-bottom: 1px solid var(--border); }
td { padding: 10px 12px; font-size: 13px; color: var(--t2); border-bottom: 1px solid rgba(255,255,255,.03); }
tr:hover td { background: rgba(255,255,255,.02); }
.slots-preview { font-size: 12px; color: var(--t3); max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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

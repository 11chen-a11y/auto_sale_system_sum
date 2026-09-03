<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getTypes, getDates, listRecords, getChartData, createRecord, updateRecord, clearBids, deleteRecord, exportRecords } from '../api/powerBid'
import { getAll as getGenerators } from '../api/generator'
import { showError } from '../utils/error'
import { saveBlob } from '../utils/download'

const types = ref([])
const dates = ref([])
const generators = ref([])
const filters = ref({ bid_date: '', bid_type: '', status: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const chartData = ref([])
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const clearing = ref(false)
const form = ref({ generator_id: null, bid_date: '', bid_type: '', price: null, volume: null })
const chartEl = ref(null)
let chart = null

async function initFilters() {
  const [t, d, g] = await Promise.all([getTypes(), getDates(), getGenerators()])
  types.value = t.data
  dates.value = d.data
  generators.value = g.data
  if (dates.value.length) filters.value.bid_date = dates.value[0]
}

function generatorName(id) {
  const g = generators.value.find(o => o.generator_id === id)
  return g ? g.generator_name : `#${id}`
}

function renderChart() {
  if (!chartEl.value || !chartData.value.length) return
  nextTick(() => {
    if (!chart) chart = echarts.init(chartEl.value)
    const series = chartData.value.map(item => ({
      name: generatorName(item.generator_id),
      type: 'bar',
      data: [{ value: item.volume, price: item.price }],
    }))
    chart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          const p = params[0]
          return `${p.name}<br/>发电商: ${p.seriesName}<br/>报价: ${p.data.price} 元/MWh<br/>容量: ${p.data.value} MWh`
        }
      },
      xAxis: { type: 'category', data: chartData.value.map((_, i) => `#${i + 1}`), axisLabel: { color: '#8a8f98' }, axisLine: { lineStyle: { color: '#2a2d34' } } },
      yAxis: { type: 'value', name: 'MWh', nameTextStyle: { color: '#8a8f98' }, axisLabel: { color: '#8a8f98' }, splitLine: { lineStyle: { color: '#2a2d34' } } },
      series: [{ type: 'bar', data: chartData.value.map(r => ({ value: r.volume, price: r.price })), itemStyle: { color: 'var(--cyan)' } }],
      backgroundColor: 'transparent',
    })
    chart.resize()
  })
}

watch(chartData, renderChart, { deep: true })

async function loadChart() {
  if (!filters.value.bid_date) return
  try {
    const res = await getChartData({ bid_date: filters.value.bid_date, bid_type: filters.value.bid_type || undefined })
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
  } finally { loading.value = false }
}

async function search() {
  page.value = 1
  await Promise.all([loadChart(), loadTable()])
}

async function doExport() {
  exporting.value = true
  try {
    const res = await exportRecords(filters.value)
    saveBlob(res, 'power_bid_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

async function doClear() {
  if (!filters.value.bid_date) return alert('请先选择日期')
  if (!confirm(`确认出清 ${filters.value.bid_date} 的报价？`)) return
  clearing.value = true
  try {
    const res = await clearBids({ bid_date: filters.value.bid_date, bid_type: filters.value.bid_type || undefined })
    alert(res.data.msg)
    await search()
  } catch (e) {
    alert(e.response?.data?.detail || '出清失败')
  } finally { clearing.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { generator_id: null, bid_date: '', bid_type: '', price: null, volume: null }
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.bid_id
  form.value = { generator_id: row.generator_id, bid_date: row.bid_date, bid_type: row.bid_type, price: row.price, volume: row.volume }
  showForm.value = true
}

async function submitForm() {
  if (editing.value) {
    await updateRecord(editing.value, form.value)
  } else {
    await createRecord(form.value)
  }
  showForm.value = false
  await search()
}

async function removeRow(id) {
  if (!confirm('确认删除？')) return
  await deleteRecord(id)
  await search()
}

onMounted(async () => {
  await initFilters()
  await search()
})
</script>

<template>
  <div class="pb-root">
    <div class="filter-bar">
      <select v-model="filters.bid_date">
        <option value="">全部日期</option>
        <option v-for="d in dates" :key="d" :value="d">{{ d }}</option>
      </select>
      <select v-model="filters.bid_type">
        <option value="">全部类型</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filters.status">
        <option value="">全部状态</option>
        <option value="待出清">待出清</option>
        <option value="已出清">已出清</option>
      </select>
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button class="btn btn-ghost" @click="openCreate">+ 报价</button>
      <button class="btn btn-ghost" :disabled="clearing" @click="doClear">⚡ 出清</button>
    </div>

    <div class="chart-wrap">
      <h3 class="section-title">报价分布</h3>
      <div v-if="!chartData.length" class="chart-empty">请选择日期后查询</div>
      <div ref="chartEl" class="chart-el" v-show="chartData.length"></div>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>日期</th><th>发电商</th><th>类型</th><th>报价 (元/MWh)</th><th>容量 (MWh)</th><th>出清价</th><th>出清量</th><th>状态</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.bid_id">
            <td>{{ r.bid_date }}</td>
            <td>{{ generatorName(r.generator_id) }}</td>
            <td><span class="tag">{{ r.bid_type }}</span></td>
            <td>{{ r.price != null ? Number(r.price).toFixed(2) : '-' }}</td>
            <td>{{ r.volume != null ? Number(r.volume).toLocaleString() : '-' }}</td>
            <td>{{ r.cleared_price != null ? Number(r.cleared_price).toFixed(2) : '-' }}</td>
            <td>{{ r.cleared_volume != null ? Number(r.cleared_volume).toLocaleString() : '-' }}</td>
            <td><span class="badge-status" :class="{ done: r.status === '已出清' }">{{ r.status }}</span></td>
            <td>
              <button v-if="r.status === '待出清'" class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.bid_id)">删除</button>
            </td>
          </tr>
          <tr v-if="!records.length">
            <td colspan="9" class="empty">暂无数据</td>
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
        <h3>{{ editing ? '编辑' : '新增' }}报价</h3>
        <div class="modal-body">
          <label>发电商
            <select v-model="form.generator_id" :disabled="!!editing">
              <option :value="null">请选择</option>
              <option v-for="g in generators" :key="g.generator_id" :value="g.generator_id">{{ g.generator_name }}</option>
            </select>
          </label>
          <label>日期 <input v-model="form.bid_date" type="date" :disabled="!!editing" /></label>
          <label>交易类型
            <select v-model="form.bid_type" :disabled="!!editing">
              <option value="">-</option>
              <option value="中长期">中长期</option>
              <option value="现货">现货</option>
              <option value="调峰">调峰</option>
            </select>
          </label>
          <label>报价 (元/MWh) <input v-model="form.price" type="number" step="0.01" /></label>
          <label>申报容量 (MWh) <input v-model="form.volume" type="number" step="0.01" /></label>
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
.pb-root { display: flex; flex-direction: column; gap: 24px; }
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
.badge-status { display: inline-block; padding: 2px 10px; border-radius: 100px; font-size: 11px; background: rgba(255,193,7,.15); color: #ffc107; }
.badge-status.done { background: rgba(0,212,170,.1); color: var(--cyan); }
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
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
</style>

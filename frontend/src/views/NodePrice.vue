<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { useUserStore } from '../stores/user'
import { getNodes, getTypes, getDates, listPrices, getChartData, createPrice, updatePrice, deletePrice, exportRecords } from '../api/nodePrice'
import { showError } from '../utils/error'
import { saveBlob } from '../utils/download'

const store = useUserStore()
const isAdmin = computed(() => store.userInfo?.role === 'admin')

const nodes = ref([])
const types = ref([])
const dates = ref([])
const filters = ref({ trade_date: '', node_name: '', price_type: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const chartData = ref([])
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const form = ref({ trade_date: '', node_name: '', price_type: '' })
const slotsText = ref('')
const chartEl = ref(null)
let chart = null

async function initFilters() {
  const [n, t, d] = await Promise.all([getNodes(), getTypes(), getDates()])
  nodes.value = n.data
  types.value = t.data
  dates.value = d.data
  if (dates.value.length) filters.value.trade_date = dates.value[0]
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
      name: `${item.node_name}${item.price_type ? ' (' + item.price_type + ')' : ''}`,
      type: 'line',
      smooth: true,
      data: item.slots ? Object.values(item.slots) : [],
      symbol: 'none',
      lineStyle: { width: 2 },
    }))
    chart.setOption({
      tooltip: { trigger: 'axis', formatter: params => {
        let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
        params.forEach(p => { html += `<div style="display:flex;justify-content:space-between;gap:24px"><span>${p.seriesName}</span><b>${p.value} 元/MWh</b></div>` })
        return html
      }},
      legend: { data: series.map(s => s.name), textStyle: { color: '#a38990' }, bottom: 0 },
      grid: { left: 60, right: 20, top: 20, bottom: 48 },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#a38990', fontSize: 10, interval: 11 }, axisLine: { lineStyle: { color: '#e0c8ce' } }, splitLine: { show: false } },
      yAxis: { type: 'value', name: '元/MWh', nameTextStyle: { color: '#a38990' }, axisLabel: { color: '#a38990' }, splitLine: { lineStyle: { color: '#e0c8ce' } } },
      series,
      backgroundColor: 'transparent',
    })
    chart.resize()
  })
}

watch(chartData, renderChart, { deep: true })

async function loadChart() {
  if (!filters.value.trade_date) return
  try {
    const res = await getChartData({ trade_date: filters.value.trade_date, node_name: filters.value.node_name || undefined, price_type: filters.value.price_type || undefined })
    chartData.value = res.data
  } catch (e) { chartData.value = []; showError(e) }
}

async function loadTable() {
  loading.value = true
  try {
    const res = await listPrices({ page: page.value, page_size: pageSize.value, ...filters.value })
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
    saveBlob(res, 'node_price_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { trade_date: '', node_name: '', price_type: '' }
  slotsText.value = ''
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.price_id
  form.value = { trade_date: row.trade_date, node_name: row.node_name, price_type: row.price_type || '' }
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
    await updatePrice(editing.value, payload)
  } else {
    await createPrice(payload)
  }
  showForm.value = false
  await search()
}

async function removeRow(id) {
  if (!confirm('确认删除？')) return
  await deletePrice(id)
  await search()
}

function parseSlotsPreview(slots) {
  if (!slots || typeof slots !== 'object') return '-'
  const vals = Object.values(slots).filter(v => v != null)
  if (!vals.length) return '-'
  const avg = (vals.reduce((a, b) => a + Number(b), 0) / vals.length).toFixed(2)
  const max = Math.max(...vals.map(Number)).toFixed(2)
  const min = Math.min(...vals.map(Number)).toFixed(2)
  return `均价 ${avg} · 最高 ${max} · 最低 ${min}`
}

onMounted(async () => {
  await initFilters()
  await search()
})
</script>

<template>
  <div class="np-root">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <select v-model="filters.trade_date">
        <option value="">全部日期</option>
        <option v-for="d in dates" :key="d" :value="d">{{ d }}</option>
      </select>
      <select v-model="filters.node_name">
        <option value="">全部节点</option>
        <option v-for="n in nodes" :key="n" :value="n">{{ n }}</option>
      </select>
      <select v-model="filters.price_type">
        <option value="">全部类型</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button v-if="isAdmin" class="btn btn-ghost" @click="openCreate">+ 新增</button>
    </div>

    <!-- 电价曲线图 -->
    <div class="chart-wrap">
      <h3 class="section-title">日内电价曲线</h3>
      <div v-if="!chartData.length" class="chart-empty">请选择日期后查询</div>
      <div ref="chartEl" class="chart-el" v-show="chartData.length"></div>
    </div>

    <!-- 数据表格 -->
    <div class="table-wrap">
      <h3 class="section-title">电价记录</h3>
      <table>
        <thead>
          <tr>
            <th>日期</th><th>节点</th><th>类型</th><th>96点概览</th><th v-if="isAdmin">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.price_id">
            <td>{{ r.trade_date }}</td>
            <td>{{ r.node_name }}</td>
            <td><span class="tag">{{ r.price_type || '-' }}</span></td>
            <td class="slots-preview">{{ parseSlotsPreview(r.slots) }}</td>
            <td v-if="isAdmin">
              <button class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.price_id)">删除</button>
            </td>
          </tr>
          <tr v-if="!records.length">
            <td :colspan="isAdmin ? 5 : 4" class="empty">暂无数据</td>
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

    <!-- 新增/编辑弹窗 -->
    <div class="modal-overlay" v-if="showForm" @click.self="showForm = false">
      <div class="modal">
        <h3>{{ editing ? '编辑' : '新增' }}电价记录</h3>
        <div class="modal-body">
          <label>日期 <input v-model="form.trade_date" type="date" :disabled="!!editing" /></label>
          <label>节点 <input v-model="form.node_name" :disabled="!!editing" /></label>
          <label>类型 <select v-model="form.price_type"><option value="">-</option><option v-for="t in types" :key="t" :value="t">{{ t }}</option></select></label>
          <label>96点数据 (JSON) <textarea v-model="slotsText" rows="4" placeholder='{"0":320.5,"1":315.2,...}'></textarea></label>
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
.np-root { display: flex; flex-direction: column; gap: 24px; }

.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.filter-bar select, .filter-bar input {
  padding: 8px 12px; background: rgba(255,105,135,.04); border: 1px solid var(--border);
  border-radius: 8px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.filter-bar select option { background: #fff5f7; }

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
.tag { display: inline-block; padding: 2px 10px; background: rgba(255,123,156,.12); border-radius: 100px; font-size: 11px; color: var(--cyan); }
.empty { text-align: center; color: var(--t3); padding: 32px !important; }
.danger { color: var(--danger) !important; }
.danger:hover { background: rgba(255,77,106,.1) !important; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 16px; font-size: 13px; color: var(--t3); }
.pagination button { padding: 6px 14px; background: rgba(255,255,255,.03); border: 1px solid var(--border); border-radius: 6px; color: var(--t2); cursor: pointer; }
.pagination button:disabled { opacity: .3; cursor: default; }
.pagination button:hover:not(:disabled) { background: rgba(255,255,255,.06); }

.modal-overlay { position: fixed; inset: 0; background: rgba(80,40,50,.35); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal { background: #fff; border: 1px solid var(--border); border-radius: var(--r); padding: 28px; min-width: 420px; max-width: 520px; }
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

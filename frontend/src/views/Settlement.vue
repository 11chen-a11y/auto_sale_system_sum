<script setup>
import { ref, onMounted } from 'vue'
import { getTypes, getMonths, listRecords, createRecord, updateRecord, confirmRecord, deleteRecord, exportRecords } from '../api/settlement'
import { saveBlob } from '../utils/download'

const types = ref([])
const months = ref([])
const filters = ref({ settle_month: '', settle_type: '', status: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const form = ref({ contract_id: null, settle_month: '', settle_type: '', volume: null, price: null, amount: null })

async function initFilters() {
  const [t, m] = await Promise.all([getTypes(), getMonths()])
  types.value = t.data
  months.value = m.data
  if (months.value.length) filters.value.settle_month = months.value[0]
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
  await loadTable()
}

async function doExport() {
  exporting.value = true
  try {
    const res = await exportRecords(filters.value)
    saveBlob(res, 'settlement_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { contract_id: null, settle_month: '', settle_type: '', volume: null, price: null, amount: null }
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.settlement_id
  form.value = { contract_id: row.contract_id, settle_month: row.settle_month, settle_type: row.settle_type, volume: row.volume, price: row.price, amount: row.amount }
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

async function doConfirm(id) {
  if (!confirm('确认结算？')) return
  await confirmRecord(id)
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
  <div class="st-root">
    <div class="filter-bar">
      <select v-model="filters.settle_month">
        <option value="">全部月份</option>
        <option v-for="m in months" :key="m" :value="m">{{ m }}</option>
      </select>
      <select v-model="filters.settle_type">
        <option value="">全部类型</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filters.status">
        <option value="">全部状态</option>
        <option value="待确认">待确认</option>
        <option value="已确认">已确认</option>
      </select>
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button class="btn btn-ghost" @click="openCreate">+ 新增</button>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>合约ID</th><th>结算月</th><th>类型</th><th>电量 (MWh)</th><th>电价 (元/MWh)</th><th>金额 (元)</th><th>状态</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.settlement_id">
            <td>{{ r.contract_id || '-' }}</td>
            <td>{{ r.settle_month }}</td>
            <td><span class="tag">{{ r.settle_type }}</span></td>
            <td>{{ r.volume != null ? Number(r.volume).toLocaleString() : '-' }}</td>
            <td>{{ r.price != null ? Number(r.price).toFixed(2) : '-' }}</td>
            <td>{{ r.amount != null ? Number(r.amount).toLocaleString() : '-' }}</td>
            <td><span class="badge-status" :class="{ confirmed: r.status === '已确认' }">{{ r.status }}</span></td>
            <td>
              <button v-if="r.status === '待确认'" class="btn btn-ghost sm" @click="doConfirm(r.settlement_id)">确认</button>
              <button class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.settlement_id)">删除</button>
            </td>
          </tr>
          <tr v-if="!records.length">
            <td colspan="8" class="empty">暂无数据</td>
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
        <h3>{{ editing ? '编辑' : '新增' }}结算</h3>
        <div class="modal-body">
          <label>合约ID <input v-model="form.contract_id" type="number" /></label>
          <label>结算月 <input v-model="form.settle_month" type="month" :disabled="!!editing" /></label>
          <label>结算类型
            <select v-model="form.settle_type" :disabled="!!editing">
              <option value="发电侧结算">发电侧结算</option>
              <option value="用户侧结算">用户侧结算</option>
            </select>
          </label>
          <label>结算电量 (MWh) <input v-model="form.volume" type="number" step="0.01" /></label>
          <label>结算电价 (元/MWh) <input v-model="form.price" type="number" step="0.01" /></label>
          <label>结算金额 (元) <input v-model="form.amount" type="number" step="0.01" /></label>
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
.st-root { display: flex; flex-direction: column; gap: 24px; }
.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.filter-bar select, .filter-bar input {
  padding: 8px 12px; background: rgba(255,255,255,.03); border: 1px solid var(--border);
  border-radius: 8px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.filter-bar select option { background: #1a1d24; }
.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 24px; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 600; letter-spacing: .08em; color: var(--t3); border-bottom: 1px solid var(--border); }
td { padding: 10px 12px; font-size: 13px; color: var(--t2); border-bottom: 1px solid rgba(255,255,255,.03); }
tr:hover td { background: rgba(255,255,255,.02); }
.tag { display: inline-block; padding: 2px 10px; background: rgba(0,212,170,.08); border-radius: 100px; font-size: 11px; color: var(--cyan); }
.badge-status { display: inline-block; padding: 2px 10px; border-radius: 100px; font-size: 11px; background: rgba(255,193,7,.15); color: #ffc107; }
.badge-status.confirmed { background: rgba(0,212,170,.1); color: var(--cyan); }
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

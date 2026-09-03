<script setup>
import { ref, onMounted } from 'vue'
import { getMonths, getCustomers, listRecords, createRecord, updateRecord, payRecord, deleteRecord, exportRecords } from '../api/bill'
import { saveBlob } from '../utils/download'

const months = ref([])
const customerOpts = ref([])
const filters = ref({ bill_month: '', payment_status: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const form = ref({ customer_id: null, bill_month: '', total_kwh: null, total_amount: null, payment_status: '未付', due_date: '' })

async function initFilters() {
  const [m, c] = await Promise.all([getMonths(), getCustomers()])
  months.value = m.data
  customerOpts.value = c.data
  if (months.value.length) filters.value.bill_month = months.value[0]
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
    saveBlob(res, 'bill_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

function customerName(id) {
  const c = customerOpts.value.find(o => o.customer_id === id)
  return c ? c.customer_name : `#${id}`
}

function openCreate() {
  editing.value = null
  form.value = { customer_id: null, bill_month: '', total_kwh: null, total_amount: null, payment_status: '未付', due_date: '' }
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.bill_id
  form.value = {
    customer_id: row.customer_id,
    bill_month: row.bill_month,
    total_kwh: row.total_kwh,
    total_amount: row.total_amount,
    payment_status: row.payment_status,
    due_date: row.due_date || '',
  }
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

async function markPaid(id) {
  if (!confirm('确认标记为已付？')) return
  await payRecord(id)
  await search()
}

async function removeRow(id) {
  if (!confirm('确认删除？')) return
  await deleteRecord(id)
  await search()
}

function statusClass(s) {
  return s === '已付' ? 'paid' : 'unpaid'
}

onMounted(async () => {
  await initFilters()
  await search()
})
</script>

<template>
  <div class="bl-root">
    <div class="filter-bar">
      <select v-model="filters.bill_month">
        <option value="">全部月份</option>
        <option v-for="m in months" :key="m" :value="m">{{ m }}</option>
      </select>
      <select v-model="filters.payment_status">
        <option value="">全部状态</option>
        <option value="未付">未付</option>
        <option value="已付">已付</option>
      </select>
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button class="btn btn-ghost" @click="openCreate">+ 新增</button>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>客户</th><th>账期</th><th>用电量 (kWh)</th><th>金额 (元)</th><th>状态</th><th>到期日</th><th>付款时间</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.bill_id">
            <td>{{ customerName(r.customer_id) }}</td>
            <td>{{ r.bill_month }}</td>
            <td>{{ r.total_kwh != null ? Number(r.total_kwh).toLocaleString() : '-' }}</td>
            <td>{{ r.total_amount != null ? Number(r.total_amount).toLocaleString() : '-' }}</td>
            <td><span class="badge-status" :class="statusClass(r.payment_status)">{{ r.payment_status }}</span></td>
            <td>{{ r.due_date || '-' }}</td>
            <td>{{ r.paid_at || '-' }}</td>
            <td>
              <button v-if="r.payment_status !== '已付'" class="btn btn-ghost sm" @click="markPaid(r.bill_id)">付款</button>
              <button class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.bill_id)">删除</button>
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
        <h3>{{ editing ? '编辑' : '新增' }}账单</h3>
        <div class="modal-body">
          <label>客户
            <select v-model="form.customer_id" :disabled="!!editing">
              <option :value="null">请选择</option>
              <option v-for="c in customerOpts" :key="c.customer_id" :value="c.customer_id">{{ c.customer_name }}</option>
            </select>
          </label>
          <label>账期 <input v-model="form.bill_month" type="month" :disabled="!!editing" /></label>
          <label>用电量 (kWh) <input v-model="form.total_kwh" type="number" step="0.01" /></label>
          <label>金额 (元) <input v-model="form.total_amount" type="number" step="0.01" /></label>
          <label>状态
            <select v-model="form.payment_status">
              <option value="未付">未付</option>
              <option value="已付">已付</option>
            </select>
          </label>
          <label>到期日 <input v-model="form.due_date" type="date" /></label>
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
.bl-root { display: flex; flex-direction: column; gap: 24px; }

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
.badge-status { display: inline-block; padding: 2px 10px; border-radius: 100px; font-size: 11px; }
.badge-status.paid { background: rgba(0,212,170,.1); color: var(--cyan); }
.badge-status.unpaid { background: rgba(255,107,107,.1); color: #ff6b6b; }
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

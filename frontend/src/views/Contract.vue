<script setup>
import { ref, onMounted } from 'vue'
import { getTypes, listRecords, createRecord, updateRecord, deleteRecord, exportRecords } from '../api/contract'
import { saveBlob } from '../utils/download'
import { getAll as getGenerators } from '../api/generator'
import { getAll as getCustomers } from '../api/customer'

const types = ref([])
const generators = ref([])
const customers = ref([])
const filters = ref({ contract_type: '', status: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const form = ref({ contract_no: '', contract_type: '', party_a: '', party_b: '', generator_id: null, customer_id: null, start_date: '', end_date: '', contracted_volume: null, contract_price: null, delivery_point: '' })

async function initFilters() {
  const [t, g, c] = await Promise.all([getTypes(), getGenerators(), getCustomers()])
  types.value = t.data
  generators.value = g.data
  customers.value = c.data
}

function entityName(id, list) {
  const item = list.find(o => o.generator_id === id || o.customer_id === id)
  return item ? (item.generator_name || item.customer_name) : `#${id}`
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
    saveBlob(res, 'contract_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { contract_no: '', contract_type: '', party_a: '', party_b: '', generator_id: null, customer_id: null, start_date: '', end_date: '', contracted_volume: null, contract_price: null, delivery_point: '' }
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.contract_id
  form.value = {
    contract_no: row.contract_no, contract_type: row.contract_type, party_a: row.party_a, party_b: row.party_b,
    generator_id: row.generator_id, customer_id: row.customer_id,
    start_date: row.start_date, end_date: row.end_date,
    contracted_volume: row.contracted_volume, contract_price: row.contract_price, delivery_point: row.delivery_point || '',
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
  <div class="ct-root">
    <div class="filter-bar">
      <select v-model="filters.contract_type">
        <option value="">全部类型</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filters.status">
        <option value="">全部状态</option>
        <option value="执行中">执行中</option>
        <option value="已完成">已完成</option>
        <option value="已终止">已终止</option>
      </select>
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button class="btn btn-ghost" @click="openCreate">+ 新增</button>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>合同编号</th><th>类型</th><th>甲方</th><th>乙方</th><th>周期</th><th>电量 (MWh)</th><th>电价 (元/MWh)</th><th>状态</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.contract_id">
            <td>{{ r.contract_no }}</td>
            <td><span class="tag">{{ r.contract_type }}</span></td>
            <td>{{ r.party_a }}</td>
            <td>{{ r.party_b }}</td>
            <td>{{ r.start_date }} ~ {{ r.end_date }}</td>
            <td>{{ r.contracted_volume != null ? Number(r.contracted_volume).toLocaleString() : '-' }}</td>
            <td>{{ r.contract_price != null ? Number(r.contract_price).toFixed(2) : '-' }}</td>
            <td><span class="badge-status" :class="r.status">{{ r.status }}</span></td>
            <td>
              <button class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.contract_id)">删除</button>
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
        <h3>{{ editing ? '编辑' : '新增' }}合约</h3>
        <div class="modal-body">
          <label>合同编号 <input v-model="form.contract_no" :disabled="!!editing" /></label>
          <label>合约类型
            <select v-model="form.contract_type" :disabled="!!editing">
              <option value="购电合同">购电合同</option>
              <option value="售电合同">售电合同</option>
            </select>
          </label>
          <label>甲方 <input v-model="form.party_a" /></label>
          <label>乙方 <input v-model="form.party_b" /></label>
          <label>关联发电商
            <select v-model="form.generator_id">
              <option :value="null">无</option>
              <option v-for="g in generators" :key="g.generator_id" :value="g.generator_id">{{ g.generator_name }}</option>
            </select>
          </label>
          <label>关联用户
            <select v-model="form.customer_id">
              <option :value="null">无</option>
              <option v-for="c in customers" :key="c.customer_id" :value="c.customer_id">{{ c.customer_name }}</option>
            </select>
          </label>
          <label>开始日期 <input v-model="form.start_date" type="date" /></label>
          <label>结束日期 <input v-model="form.end_date" type="date" /></label>
          <label>合同电量 (MWh) <input v-model="form.contracted_volume" type="number" step="0.01" /></label>
          <label>合同电价 (元/MWh) <input v-model="form.contract_price" type="number" step="0.01" /></label>
          <label>交割点 <input v-model="form.delivery_point" /></label>
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
.ct-root { display: flex; flex-direction: column; gap: 24px; }
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
.badge-status { display: inline-block; padding: 2px 10px; border-radius: 100px; font-size: 11px; }
.badge-status.执行中 { background: rgba(0,212,170,.1); color: var(--cyan); }
.badge-status.已完成 { background: rgba(99,179,237,.1); color: #63b3ed; }
.badge-status.已终止 { background: rgba(255,107,107,.1); color: #ff6b6b; }
.empty { text-align: center; color: var(--t3); padding: 32px !important; }
.danger { color: #ff6b6b !important; }
.danger:hover { background: rgba(255,107,107,.1) !important; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 16px; font-size: 13px; color: var(--t3); }
.pagination button { padding: 6px 14px; background: rgba(255,255,255,.03); border: 1px solid var(--border); border-radius: 6px; color: var(--t2); cursor: pointer; }
.pagination button:disabled { opacity: .3; cursor: default; }
.pagination button:hover:not(:disabled) { background: rgba(255,255,255,.06); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal { background: #1a1d24; border: 1px solid var(--border); border-radius: var(--r); padding: 28px; min-width: 480px; max-width: 600px; }
.modal h3 { font-family: 'Cormorant Garamond', serif; font-size: 1.3rem; margin-bottom: 20px; }
.modal-body { display: flex; flex-direction: column; gap: 14px; max-height: 60vh; overflow-y: auto; }
.modal-body label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--t3); }
.modal-body input, .modal-body select, .modal-body textarea {
  padding: 8px 10px; background: rgba(255,255,255,.03); border: 1px solid var(--border);
  border-radius: 6px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.modal-body select option { background: #1a1d24; }
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
</style>

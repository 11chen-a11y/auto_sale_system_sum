<script setup>
import { ref, onMounted } from 'vue'
import { getTypes, getVoltages, listRecords, createRecord, updateRecord, deleteRecord, exportRecords } from '../api/customer'
import { saveBlob } from '../utils/download'

const types = ref([])
const voltages = ref([])
const filters = ref({ customer_name: '', customer_type: '', voltage_level: '' })
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const exporting = ref(false)
const showForm = ref(false)
const editing = ref(null)
const form = ref({ customer_name: '', customer_type: '', voltage_level: '', contract_cap: null, address: '', contact_name: '', contact_phone: '' })

async function initFilters() {
  const [t, v] = await Promise.all([getTypes(), getVoltages()])
  types.value = t.data
  voltages.value = v.data
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
    saveBlob(res, 'customer_export.csv')
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally { exporting.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { customer_name: '', customer_type: '', voltage_level: '', contract_cap: null, address: '', contact_name: '', contact_phone: '' }
  showForm.value = true
}

function openEdit(row) {
  editing.value = row.customer_id
  form.value = { customer_name: row.customer_name, customer_type: row.customer_type || '', voltage_level: row.voltage_level || '', contract_cap: row.contract_cap, address: row.address || '', contact_name: row.contact_name || '', contact_phone: row.contact_phone || '' }
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

function statusText(s) {
  return s === 1 ? '正常' : '禁用'
}

onMounted(async () => {
  await initFilters()
  await search()
})
</script>

<template>
  <div class="cu-root">
    <div class="filter-bar">
      <input v-model="filters.customer_name" placeholder="客户名称" />
      <select v-model="filters.customer_type">
        <option value="">全部类型</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filters.voltage_level">
        <option value="">全部电压</option>
        <option v-for="v in voltages" :key="v" :value="v">{{ v }}</option>
      </select>
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn btn-ghost" :disabled="exporting" @click="doExport">{{ exporting ? '导出中...' : '导出' }}</button>
      <button class="btn btn-ghost" @click="openCreate">+ 新增</button>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>名称</th><th>类型</th><th>电压等级</th><th>合同容量</th><th>联系人</th><th>电话</th><th>状态</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.customer_id">
            <td>{{ r.customer_name }}</td>
            <td><span class="tag">{{ r.customer_type || '-' }}</span></td>
            <td>{{ r.voltage_level || '-' }}</td>
            <td>{{ r.contract_cap != null ? Number(r.contract_cap).toLocaleString() + ' kVA' : '-' }}</td>
            <td>{{ r.contact_name || '-' }}</td>
            <td>{{ r.contact_phone || '-' }}</td>
            <td><span class="badge-status" :class="{ on: r.status === 1 }">{{ statusText(r.status) }}</span></td>
            <td>
              <button class="btn btn-ghost sm" @click="openEdit(r)">编辑</button>
              <button class="btn btn-ghost sm danger" @click="removeRow(r.customer_id)">删除</button>
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
        <h3>{{ editing ? '编辑' : '新增' }}客户</h3>
        <div class="modal-body">
          <label>客户名称 <input v-model="form.customer_name" :disabled="!!editing" /></label>
          <label>客户类型 <input v-model="form.customer_type" /></label>
          <label>电压等级
            <select v-model="form.voltage_level">
              <option value="">-</option>
              <option value="10kV">10kV</option>
              <option value="35kV">35kV</option>
              <option value="110kV">110kV</option>
              <option value="220kV">220kV</option>
              <option v-for="v in voltages" :key="v" :value="v">{{ v }}</option>
            </select>
          </label>
          <label>合同容量 (kVA) <input v-model="form.contract_cap" type="number" step="0.01" /></label>
          <label>地址 <input v-model="form.address" /></label>
          <label>联系人 <input v-model="form.contact_name" /></label>
          <label>联系电话 <input v-model="form.contact_phone" /></label>
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
.cu-root { display: flex; flex-direction: column; gap: 24px; }

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
.badge-status { display: inline-block; padding: 2px 10px; border-radius: 100px; font-size: 11px; background: rgba(255,107,107,.1); color: #ff6b6b; }
.badge-status.on { background: rgba(0,212,170,.1); color: var(--cyan); }
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

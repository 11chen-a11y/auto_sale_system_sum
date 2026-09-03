<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['close', 'imported'])

const API_BASE = 'http://localhost:8000'
const modules = [
  { key: 'node-price', label: '节点电价', baseURL: `${API_BASE}/node-price` },
  { key: 'load-data', label: '负荷数据', baseURL: `${API_BASE}/load-data` },
  { key: 'new-energy', label: '新能源出力', baseURL: `${API_BASE}/new-energy` },
  { key: 'spot-trade', label: '现货交易', baseURL: `${API_BASE}/spot-trade` },
  { key: 'weather', label: '天气数据', baseURL: `${API_BASE}/weather` },
  { key: 'customer', label: '客户档案', baseURL: `${API_BASE}/customer` },
  { key: 'bill', label: '账单管理', baseURL: `${API_BASE}/bill` },
  { key: 'generator', label: '发电商管理', baseURL: `${API_BASE}/generator` },
  { key: 'power-bid', label: '报价/竞价', baseURL: `${API_BASE}/power-bid` },
  { key: 'contract', label: '合约管理', baseURL: `${API_BASE}/contract` },
  { key: 'settlement', label: '交易结算', baseURL: `${API_BASE}/settlement` },
]

const selected = ref(modules[0])
const jsonText = ref('')
const importing = ref(false)
const result = ref('')

const examples = {
  'node-price': '[{"trade_date":"2026-07-25","node_name":"节点A","price_type":"日前","slots":{"0":320.5,"1":315.2}}]',
  'load-data': '[{"record_date":"2026-07-25","data_type":"实际负荷","slots":{"0":320.5,"1":315.2}}]',
  'new-energy': '[{"record_date":"2026-07-25","station_name":"风场A","energy_type":"风电","forecast_slots":{"0":120.5},"actual_slots":{"0":125.8}}]',
  'spot-trade': '[{"trade_month":"2026-07","trade_type":"日前","avg_price":350.5,"volume":1000}]',
  'weather': '[{"station_name":"站A","city":"北京","record_date":"2026-07-25","data_type":"日均温","temperature":32.5}]',
  'customer': '[{"customer_name":"用户A","customer_type":"大工业","voltage_level":"10kV","contact_phone":"13800138000"}]',
  'bill': '[{"customer_id":1,"bill_month":"2026-07","total_kwh":10000,"total_amount":5000,"payment_status":"未付"}]',
  'generator': '[{"generator_name":"电厂A","generator_type":"火电","capacity":1000,"location":"河北"}]',
  'power-bid': '[{"generator_id":1,"bid_date":"2026-07-25","bid_type":"中长期","price":350,"volume":500}]',
  'contract': '[{"contract_no":"CT-2026-001","contract_type":"购电合同","party_a":"售电公司","party_b":"电厂A","start_date":"2026-01-01","end_date":"2026-12-31","contracted_volume":10000,"contract_price":350}]',
  'settlement': '[{"contract_id":1,"settle_month":"2026-07","settle_type":"发电侧结算","volume":1000,"price":350,"amount":350000}]',
}

function loadExample() {
  jsonText.value = examples[selected.value.key] || ''
}

async function doImport() {
  let data
  try {
    data = JSON.parse(jsonText.value)
    if (!Array.isArray(data)) throw new Error('必须是数组')
  } catch (e) {
    alert('JSON 格式错误: ' + e.message)
    return
  }
  if (!data.length) { alert('数据为空'); return }

  importing.value = true
  result.value = ''
  try {
    const res = await axios.post(`${selected.value.baseURL}/batch`, data, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    result.value = res.data.msg || '导入成功'
    emit('imported')
  } catch (e) {
    result.value = '导入失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h3>批量导入</h3>
      <div class="modal-body">
        <label>目标模块
          <select v-model="selected">
            <option v-for="m in modules" :key="m.key" :value="m">{{ m.label }}</option>
          </select>
        </label>
        <label>
          <div class="label-row">
            <span>数据 (JSON 数组)</span>
            <button class="btn btn-ghost sm" @click="loadExample">加载示例</button>
          </div>
          <textarea v-model="jsonText" rows="10" placeholder='[{...},{...}]'></textarea>
        </label>
        <div v-if="result" class="result" :class="{ error: result.includes('失败') }">{{ result }}</div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" :disabled="importing" @click="doImport">
          {{ importing ? '导入中...' : '开始导入' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 200; display: flex; align-items: center; justify-content: center; }
.modal { background: #1a1d24; border: 1px solid var(--border); border-radius: var(--r); padding: 28px; min-width: 480px; max-width: 640px; width: 90%; }
.modal h3 { font-family: 'Cormorant Garamond', serif; font-size: 1.3rem; margin-bottom: 20px; }
.modal-body { display: flex; flex-direction: column; gap: 14px; }
.modal-body label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--t3); }
.modal-body select, .modal-body textarea {
  padding: 8px 10px; background: rgba(255,255,255,.03); border: 1px solid var(--border);
  border-radius: 6px; color: var(--t1); font-family: 'Outfit', sans-serif; font-size: 13px;
}
.modal-body select option { background: #1a1d24; }
.modal-body textarea { resize: vertical; font-family: 'Courier New', monospace; font-size: 12px; }
.label-row { display: flex; justify-content: space-between; align-items: center; }
.result { padding: 10px 14px; border-radius: 8px; font-size: 13px; background: rgba(0,212,170,.08); color: var(--cyan); }
.result.error { background: rgba(255,107,107,.1); color: #ff6b6b; }
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
.sm { padding: 6px 12px; font-size: 11px; }
</style>

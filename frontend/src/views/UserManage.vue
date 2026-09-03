<script setup>
import { ref, onMounted } from 'vue'
import { listUsers, setUserRole } from '../api/user'
import { useUserStore } from '../stores/user'

const store = useUserStore()
const users = ref([])
const loading = ref(false)
const msg = ref('')

async function load() {
  loading.value = true
  try {
    const res = await listUsers()
    users.value = res.data
  } finally { loading.value = false }
}

async function toggleRole(u) {
  const next = u.role === 'admin' ? 'viewer' : 'admin'
  const action = next === 'admin' ? '设为管理员' : '取消管理员'
  if (!confirm(`确认将用户「${u.username}」${action}？`)) return
  msg.value = ''
  try {
    await setUserRole(u.user_id, next)
    await load()
  } catch (e) {
    msg.value = e.response?.data?.detail || '操作失败'
  }
}

function roleText(r) {
  return r === 'admin' ? '管理员' : '普通用户'
}

onMounted(load)
</script>

<template>
  <div class="cu-root">
    <div class="filter-bar">
      <span class="hint">管理平台账号角色，只有管理员可以访问业务功能模块</span>
      <button class="btn btn-ghost" @click="load">刷新</button>
    </div>

    <p v-if="msg" class="error">{{ msg }}</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>用户名</th><th>姓名</th><th>角色</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.user_id">
            <td>{{ u.user_id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.real_name || '-' }}</td>
            <td>
              <span class="badge-status" :class="{ on: u.role === 'admin' }">{{ roleText(u.role) }}</span>
            </td>
            <td>
              <button v-if="u.role !== 'admin'" class="btn btn-ghost sm" @click="toggleRole(u)">设为管理员</button>
              <button v-else class="btn btn-ghost sm danger" :disabled="u.user_id === store.userInfo?.user_id" @click="toggleRole(u)">取消管理员</button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="5" class="empty">暂无用户</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.hint { color: var(--t3); font-size: 13px; }
.error { color: var(--danger, #e74c3c); font-size: 13px; }
</style>

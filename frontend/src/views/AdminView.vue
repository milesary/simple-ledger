<template>
  <div class="page-container">
    <header class="page-heading">
      <div>
        <p class="eyebrow">权限与账号</p>
        <h1>账号管理</h1>
        <p>查询注册账号，管理登录状态、管理员角色和密码。</p>
      </div>
    </header>

    <section class="metric-grid metric-grid--admin">
      <article class="metric-card">
        <div class="metric-card__top">
          <span>匹配账号</span>
          <Users :size="19" />
        </div>
        <strong>{{ data.total_count }}</strong>
        <small>当前筛选结果</small>
      </article>
      <article class="metric-card">
        <div class="metric-card__top">
          <span>正常账号</span>
          <UserCheck :size="19" />
        </div>
        <strong class="is-income">{{ data.active_count }}</strong>
        <small>可以正常登录</small>
      </article>
      <article class="metric-card">
        <div class="metric-card__top">
          <span>管理员</span>
          <ShieldCheck :size="19" />
        </div>
        <strong>{{ data.admin_count }}</strong>
        <small>拥有后台权限</small>
      </article>
    </section>

    <form class="filter-panel filter-panel--admin" @submit.prevent="search">
      <label class="filter-panel__search">
        <span>账号查询</span>
        <input v-model.trim="keyword" type="search" placeholder="搜索邮箱或用户 ID" />
      </label>
      <div class="filter-panel__actions">
        <button class="primary-button" type="submit">
          <Search :size="17" />
          搜索
        </button>
        <button class="secondary-button" type="button" @click="resetSearch">
          重置
        </button>
      </div>
    </form>

    <article class="content-card">
      <div class="card-heading card-heading--table">
        <div>
          <span>账号列表</span>
          <h2>{{ data.total_count }} 个账号</h2>
        </div>
        <button
          class="icon-button"
          type="button"
          aria-label="刷新账号列表"
          title="刷新"
          :disabled="loading"
          @click="load"
        >
          <RefreshCw :class="{ spin: loading }" :size="18" />
        </button>
      </div>

      <div v-if="loading" class="loading-panel">
        <LoaderCircle class="spin" :size="24" />
        正在加载账号...
      </div>

      <div v-else-if="error" class="error-panel">
        <CircleAlert :size="22" />
        <span>{{ error }}</span>
        <button class="secondary-button" type="button" @click="load">重试</button>
      </div>

      <div v-else-if="data.users.length" class="table-scroll">
        <table class="data-table admin-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>邮箱</th>
              <th>角色</th>
              <th>状态</th>
              <th>注册时间</th>
              <th>最后登录</th>
              <th class="align-center">管理操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in data.users" :key="item.id">
              <td class="nowrap">{{ item.id }}</td>
              <td class="nowrap">{{ item.email }}</td>
              <td>
                <span class="category-badge">
                  {{ item.is_admin ? '管理员' : '普通用户' }}
                </span>
              </td>
              <td>
                <span class="status-pill" :class="item.is_active ? 'success' : 'error'">
                  {{ item.is_active ? '正常' : '已禁用' }}
                </span>
              </td>
              <td class="nowrap">{{ formatDateTime(item.created_at) }}</td>
              <td class="nowrap">
                {{ item.last_login_at ? formatDateTime(item.last_login_at) : '从未登录' }}
              </td>
              <td>
                <div class="admin-actions">
                  <button
                    class="secondary-button"
                    type="button"
                    :disabled="busyId === item.id || item.id === data.current_user_id"
                    @click="toggleUser(item)"
                  >
                    {{ item.is_active ? '禁用' : '启用' }}
                  </button>
                  <button
                    class="secondary-button"
                    type="button"
                    :disabled="busyId === item.id || item.id === data.current_user_id"
                    @click="toggleRole(item)"
                  >
                    {{ item.is_admin ? '取消管理员' : '设为管理员' }}
                  </button>
                  <button
                    class="secondary-button"
                    type="button"
                    :disabled="busyId === item.id"
                    @click="openReset(item)"
                  >
                    重置密码
                  </button>
                  <button
                    class="secondary-button danger-button"
                    type="button"
                    :disabled="busyId === item.id || item.is_admin || item.id === data.current_user_id"
                    @click="openDelete(item)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <EmptyState
        v-else
        title="没有匹配账号"
        description="调整邮箱或用户 ID 后重新查询。"
      />
    </article>

    <div v-if="resetTarget" class="modal-backdrop" @click.self="closeReset">
      <form class="modal-card" @submit.prevent="submitReset">
        <div class="card-heading">
          <div>
            <span>重置密码</span>
            <h2>{{ resetTarget.email }}</h2>
          </div>
          <button
            class="icon-button"
            type="button"
            aria-label="关闭"
            @click="closeReset"
          >
            <X :size="18" />
          </button>
        </div>

        <label class="field">
          <span>新密码</span>
          <input
            v-model="newPassword"
            type="password"
            minlength="8"
            maxlength="20"
            placeholder="8-20 位，包含字母和数字"
            required
          />
        </label>

        <p v-if="resetError" class="form-message form-message--error">
          {{ resetError }}
        </p>

        <div class="form-actions">
          <button class="primary-button" type="submit" :disabled="resetting">
            <LoaderCircle v-if="resetting" class="spin" :size="18" />
            {{ resetting ? '提交中...' : '确认重置' }}
          </button>
          <button class="secondary-button" type="button" @click="closeReset">
            取消
          </button>
        </div>
      </form>
    </div>

    <div v-if="deleteTarget" class="modal-backdrop" @click.self="closeDelete">
      <form class="modal-card delete-modal" @submit.prevent="submitDelete">
        <div class="card-heading">
          <div>
            <span>删除账号</span>
            <h2>{{ deleteTarget.email }}</h2>
          </div>
          <button
            class="icon-button"
            type="button"
            aria-label="关闭"
            :disabled="deleting"
            @click="closeDelete"
          >
            <X :size="18" />
          </button>
        </div>

        <div class="delete-warning">
          <TriangleAlert :size="22" />
          <p>
            该账号下的流水、账户、转账、周期规则、预算和登录验证码记录也会永久删除，
            此操作无法恢复。
          </p>
        </div>

        <p v-if="deleteError" class="form-message form-message--error">
          {{ deleteError }}
        </p>

        <div class="form-actions">
          <button class="delete-confirm-button" type="submit" :disabled="deleting">
            <LoaderCircle v-if="deleting" class="spin" :size="18" />
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
          <button
            class="secondary-button"
            type="button"
            :disabled="deleting"
            @click="closeDelete"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  CircleAlert,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldCheck,
  TriangleAlert,
  UserCheck,
  Users,
  X,
} from 'lucide-vue-next'
import { adminApi } from '../api/admin'
import EmptyState from '../components/EmptyState.vue'
import { formatDateTime } from '../utils/format'

const loading = ref(true)
const error = ref('')
const keyword = ref('')
const busyId = ref(null)
const resetTarget = ref(null)
const newPassword = ref('')
const resetting = ref(false)
const resetError = ref('')
const deleteTarget = ref(null)
const deleting = ref(false)
const deleteError = ref('')
const data = ref({
  users: [],
  total_count: 0,
  active_count: 0,
  admin_count: 0,
  current_user_id: null,
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await adminApi.users({ q: keyword.value })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function search() {
  load()
}

function resetSearch() {
  keyword.value = ''
  load()
}

async function runAction(item, action) {
  busyId.value = item.id
  error.value = ''
  try {
    await action()
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busyId.value = null
  }
}

function toggleUser(item) {
  const action = item.is_active ? '禁用' : '启用'
  if (!window.confirm(`确定${action}账号 ${item.email} 吗？`)) return
  runAction(item, () => adminApi.toggleUser(item.id))
}

function toggleRole(item) {
  const action = item.is_admin ? '取消管理员权限' : '授予管理员权限'
  if (!window.confirm(`确定对 ${item.email} ${action}吗？`)) return
  runAction(item, () => adminApi.toggleRole(item.id))
}

function openReset(item) {
  resetTarget.value = item
  newPassword.value = ''
  resetError.value = ''
}

function closeReset() {
  if (resetting.value) return
  resetTarget.value = null
  newPassword.value = ''
  resetError.value = ''
}

async function submitReset() {
  if (!resetTarget.value) return
  if (
    newPassword.value.length < 8 ||
    newPassword.value.length > 20 ||
    !/[A-Za-z]/.test(newPassword.value) ||
    !/\d/.test(newPassword.value)
  ) {
    resetError.value = '密码需为 8-20 位，并同时包含字母和数字'
    return
  }

  resetting.value = true
  resetError.value = ''
  try {
    await adminApi.resetPassword(resetTarget.value.id, newPassword.value)
    closeReset()
  } catch (err) {
    resetError.value = err.message
  } finally {
    resetting.value = false
  }
}

function openDelete(item) {
  deleteTarget.value = item
  deleteError.value = ''
}

function closeDelete() {
  if (deleting.value) return
  deleteTarget.value = null
  deleteError.value = ''
}

async function submitDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await adminApi.removeUser(deleteTarget.value.id)
    deleteTarget.value = null
    await load()
  } catch (err) {
    deleteError.value = err.message
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

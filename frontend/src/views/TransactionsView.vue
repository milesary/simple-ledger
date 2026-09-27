<template>
  <div class="page-container">
    <header class="page-heading">
      <div>
        <p class="eyebrow">流水管理</p>
        <h1>收入与支出</h1>
        <p>筛选、编辑和维护你的全部流水记录。</p>
      </div>
      <RouterLink class="primary-button" :to="{ name: 'transaction-new' }">
        <Plus :size="18" />
        新增流水
      </RouterLink>
    </header>

    <form class="filter-panel" @submit.prevent="applyFilters">
      <label>
        <span>月份</span>
        <input v-model="filters.month" type="month" />
      </label>

      <label>
        <span>分类</span>
        <select v-model="filters.category">
          <option value="">全部分类</option>
          <option v-for="item in categories" :key="item.id" :value="item.id">
            {{ item.name }}
          </option>
        </select>
      </label>

      <label>
        <span>类型</span>
        <select v-model="filters.type">
          <option value="">全部类型</option>
          <option value="income">收入</option>
          <option value="expense">支出</option>
        </select>
      </label>

      <label>
        <span>账户</span>
        <select v-model="filters.account">
          <option value="">全部账户</option>
          <option v-for="item in accounts" :key="item.id" :value="item.id">
            {{ item.name }}
          </option>
        </select>
      </label>

      <label class="filter-panel__search">
        <span>备注</span>
        <input v-model.trim="filters.q" type="search" placeholder="搜索备注..." />
      </label>

      <div class="filter-panel__actions">
        <button class="primary-button" type="submit">
          <Search :size="17" />
          筛选
        </button>
        <button class="secondary-button" type="button" @click="resetFilters">
          重置
        </button>
      </div>
    </form>

    <article class="content-card">
      <div class="card-heading card-heading--table">
        <div>
          <span>匹配结果</span>
          <h2>{{ result.total }} 条流水</h2>
        </div>
        <button
          class="icon-button"
          type="button"
          title="刷新"
          aria-label="刷新流水"
          :disabled="loading"
          @click="load"
        >
          <RefreshCw :class="{ spin: loading }" :size="18" />
        </button>
      </div>

      <div v-if="loading" class="loading-panel">
        <LoaderCircle class="spin" :size="24" />
        正在加载流水...
      </div>

      <div v-else-if="error" class="error-panel">
        <CircleAlert :size="22" />
        <span>{{ error }}</span>
        <button class="secondary-button" type="button" @click="load">重试</button>
      </div>

      <div v-else-if="result.transactions.length" class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>类型</th>
              <th>分类</th>
              <th>账户</th>
              <th>支付方式</th>
              <th>备注</th>
              <th class="align-right">金额</th>
              <th class="align-center">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in result.transactions" :key="item.id">
              <td class="nowrap">{{ formatDate(item.occurred_on) }}</td>
              <td>
                <span class="status-pill" :class="item.type">
                  {{ item.type === 'income' ? '收入' : '支出' }}
                </span>
              </td>
              <td>{{ item.category_name }}</td>
              <td>{{ item.account_name || '-' }}</td>
              <td>{{ item.payment_method || '-' }}</td>
              <td class="table-note">{{ item.note || '-' }}</td>
              <td
                class="align-right amount-cell"
                :class="item.type === 'income' ? 'is-income' : 'is-expense'"
              >
                {{ item.type === 'income' ? '+' : '-' }}{{ formatCurrency(item.amount) }}
              </td>
              <td>
                <div class="row-actions">
                  <RouterLink
                    class="icon-button"
                    :to="{ name: 'transaction-edit', params: { id: item.id } }"
                    title="编辑"
                    aria-label="编辑流水"
                  >
                    <Pencil :size="16" />
                  </RouterLink>
                  <button
                    class="icon-button icon-button--danger"
                    type="button"
                    title="删除"
                    aria-label="删除流水"
                    :disabled="deletingId === item.id"
                    @click="remove(item)"
                  >
                    <LoaderCircle v-if="deletingId === item.id" class="spin" :size="16" />
                    <Trash2 v-else :size="16" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <EmptyState
        v-else
        title="没有符合条件的流水"
        description="调整筛选条件，或者先记录一笔新的收支。"
      >
        <RouterLink class="primary-button" :to="{ name: 'transaction-new' }">
          记一笔
        </RouterLink>
      </EmptyState>
    </article>

    <nav v-if="result.pages > 1" class="pagination" aria-label="流水分页">
      <button
        class="secondary-button"
        type="button"
        :disabled="!result.has_prev || loading"
        @click="goToPage(result.page - 1)"
      >
        上一页
      </button>

      <button
        v-for="page in pageItems"
        :key="page"
        class="pagination__page"
        :class="{ active: page === result.page }"
        type="button"
        :disabled="page === result.page || loading"
        @click="goToPage(page)"
      >
        {{ page }}
      </button>

      <button
        class="secondary-button"
        type="button"
        :disabled="!result.has_next || loading"
        @click="goToPage(result.page + 1)"
      >
        下一页
      </button>
    </nav>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  CircleAlert,
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-vue-next'
import { transactionsApi } from '../api/transactions'
import { accountsApi } from '../api/accounts'
import EmptyState from '../components/EmptyState.vue'
import { formatCurrency, formatDate } from '../utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const categories = ref([])
const accounts = ref([])
const deletingId = ref(null)
const filters = reactive({
  month: String(route.query.month || ''),
  category: String(route.query.category || ''),
  account: String(route.query.account || ''),
  type: String(route.query.type || ''),
  q: String(route.query.q || ''),
  page: Number(route.query.page) || 1,
})
const result = ref({
  transactions: [],
  total: 0,
  page: 1,
  page_size: 20,
  pages: 1,
  has_next: false,
  has_prev: false,
})

const pageItems = computed(() => {
  const pages = result.value.pages
  const current = result.value.page
  const start = Math.max(1, Math.min(current - 2, pages - 4))
  const end = Math.min(pages, start + 4)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    result.value = await transactionsApi.list({
      month: filters.month,
      category: filters.category,
      account: filters.account,
      type: filters.type,
      q: filters.q,
      page: filters.page,
    })
  } catch (err) {
    if (err.status !== 401) error.value = err.message
  } finally {
    loading.value = false
  }
}

function syncQuery() {
  const query = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value !== 1),
  )
  router.replace({ name: 'transactions', query })
}

function applyFilters() {
  filters.page = 1
  syncQuery()
  load()
}

function resetFilters() {
  Object.assign(filters, {
    month: '',
    category: '',
    account: '',
    type: '',
    q: '',
    page: 1,
  })
  syncQuery()
  load()
}

function goToPage(page) {
  if (page < 1 || page > result.value.pages) return
  filters.page = page
  syncQuery()
  load()
}

async function remove(item) {
  if (!window.confirm(`确定删除这条流水吗？\n${item.category_name} ${formatCurrency(item.amount)}`)) {
    return
  }

  deletingId.value = item.id
  try {
    await transactionsApi.remove(item.id)
    if (result.value.transactions.length === 1 && filters.page > 1) {
      filters.page -= 1
      syncQuery()
    }
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    deletingId.value = null
  }
}

onMounted(async () => {
  try {
    const [categoryResult, accountResult] = await Promise.all([
      transactionsApi.categories(),
      accountsApi.list(),
    ])
    categories.value = categoryResult.categories
    accounts.value = accountResult.accounts
  } catch {
    categories.value = []
    accounts.value = []
  }
  load()
})
</script>

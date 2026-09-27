<template>
  <div class="page-container">
    <header class="page-heading">
      <div>
        <h1>你的收支一览</h1>
        <p>用趋势、分类和预算看清每一笔钱流向哪里。</p>
      </div>
    </header>

    <div v-if="loading" class="loading-panel">
      <LoaderCircle class="spin" :size="24" />
      正在加载概览数据...
    </div>

    <div v-else-if="error" class="error-panel">
      <CircleAlert :size="22" />
      <span>{{ error }}</span>
      <button class="secondary-button" type="button" @click="load">重试</button>
    </div>

    <template v-else>
      <section class="metric-grid">
        <article class="metric-card metric-card--balance">
          <div class="metric-card__top">
            <span>本月结余</span>
            <Scale :size="19" />
          </div>
          <strong :class="data.summary.balance >= 0 ? 'is-income' : 'is-expense'">
            {{ formatCurrency(data.summary.balance) }}
          </strong>
          <small>收入减去支出</small>
        </article>

        <article class="metric-card">
          <div class="metric-card__top">
            <span>本月收入</span>
            <TrendingUp :size="19" />
          </div>
          <strong class="is-income">{{ formatCurrency(data.summary.income) }}</strong>
          <small>{{ data.summary.income_count }} 笔收入</small>
        </article>

        <article class="metric-card">
          <div class="metric-card__top">
            <span>本月支出</span>
            <TrendingDown :size="19" />
          </div>
          <strong class="is-expense">{{ formatCurrency(data.summary.expense) }}</strong>
          <small>{{ data.summary.expense_count }} 笔支出</small>
        </article>

        <article class="metric-card">
          <div class="metric-card__top">
            <span>账户总余额</span>
            <WalletCards :size="19" />
          </div>
          <strong :class="data.account_summary.total_balance >= 0 ? 'is-income' : 'is-expense'">
            {{ formatCurrency(data.account_summary.total_balance) }}
          </strong>
          <small>
            <RouterLink :to="{ name: 'accounts' }">
              {{ data.account_summary.count }} 个账户
            </RouterLink>
          </small>
        </article>
      </section>

      <section class="dashboard-grid dashboard-grid--charts">
        <article class="content-card content-card--wide">
          <div class="card-heading">
            <div>
              <span>趋势分析</span>
              <h2>月度收支趋势</h2>
            </div>
            <div class="chart-legend">
              <span><i class="legend-dot legend-dot--income"></i>收入</span>
              <span><i class="legend-dot legend-dot--expense"></i>支出</span>
              <select :value="year" aria-label="选择趋势年份" @change="changeYear">
                <option v-for="item in years" :key="item" :value="item">
                  {{ item }} 年
                </option>
              </select>
            </div>
          </div>
          <TrendChart :trend="data.trend" />
        </article>

        <article class="content-card">
          <div class="card-heading">
            <div>
              <span>结构分析</span>
              <h2>支出分类占比</h2>
            </div>
          </div>
          <CategoryDonut :categories="data.categories" />
        </article>
      </section>

      <section class="dashboard-grid dashboard-grid--details">
        <article class="content-card">
          <div class="card-heading">
            <div>
              <span>消费控制</span>
              <h2>本月预算</h2>
            </div>
            <RouterLink :to="{ name: 'budgets' }">管理</RouterLink>
          </div>

          <div v-if="data.budget" class="budget-summary">
            <div class="budget-summary__amount">
              <strong>{{ formatCurrency(data.summary.expense) }}</strong>
              <span>/ {{ formatCurrency(data.budget.amount) }}</span>
            </div>
            <div class="progress-track">
              <span
                :class="{ over: data.budget.usage_percent > 100 }"
                :style="{ width: `${Math.min(data.budget.usage_percent, 100)}%` }"
              ></span>
            </div>
            <div class="budget-summary__meta">
              <span>已用 {{ Number(data.budget.usage_percent).toFixed(1) }}%</span>
              <strong :class="{ 'is-expense': data.budget.remaining < 0 }">
                剩余 {{ formatCurrency(data.budget.remaining) }}
              </strong>
            </div>
          </div>

          <EmptyState
            v-else
            title="还未设置本月预算"
            description="设置支出上限后可以实时查看使用率。"
          >
            <RouterLink class="secondary-button" :to="{ name: 'budgets' }">
              去设置
            </RouterLink>
          </EmptyState>
        </article>

        <article class="content-card content-card--wide">
          <div class="card-heading">
            <div>
              <span>最近记录</span>
              <h2>最近流水</h2>
            </div>
            <RouterLink :to="{ name: 'transactions' }">查看全部</RouterLink>
          </div>

          <div v-if="data.recent_transactions.length" class="transaction-list">
            <RouterLink
              v-for="item in data.recent_transactions"
              :key="item.id"
              class="transaction-row"
              :to="{ name: 'transaction-edit', params: { id: item.id } }"
            >
              <span class="transaction-row__date">{{ formatDate(item.occurred_on).slice(5) }}</span>
              <span class="category-badge">{{ item.category_name }}</span>
              <span class="transaction-row__note">{{ item.note || item.payment_method || '-' }}</span>
              <strong :class="item.type === 'income' ? 'is-income' : 'is-expense'">
                {{ item.type === 'income' ? '+' : '-' }}{{ formatCurrency(item.amount) }}
              </strong>
            </RouterLink>
          </div>

          <EmptyState
            v-else
            title="还没有流水"
            description="记录第一笔收入或支出后，这里会显示最近动态。"
          >
            <RouterLink class="primary-button" :to="{ name: 'transaction-new' }">
              记第一笔
            </RouterLink>
          </EmptyState>
        </article>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  CircleAlert,
  LoaderCircle,
  Scale,
  TrendingDown,
  TrendingUp,
  WalletCards,
} from 'lucide-vue-next'
import { dashboardApi } from '../api/dashboard'
import CategoryDonut from '../components/CategoryDonut.vue'
import EmptyState from '../components/EmptyState.vue'
import TrendChart from '../components/TrendChart.vue'
import { currentMonthString, formatCurrency, formatDate } from '../utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const currentMonth = currentMonthString()
const data = ref({
  current_month: currentMonth,
  current_year: new Date().getFullYear(),
  summary: {
    income: 0,
    expense: 0,
    balance: 0,
    income_count: 0,
    expense_count: 0,
  },
  trend: [],
  categories: [],
  budget: null,
  account_summary: {
    count: 0,
    total_balance: 0,
  },
  recent_transactions: [],
})
let controller = null

const year = computed(() => Number(route.query.year) || new Date().getFullYear())
const years = computed(() => {
  const current = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, index) => current - index)
})

async function load() {
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = ''

  try {
    data.value = await dashboardApi.get({
      year: year.value,
      signal: controller.signal,
    })
  } catch (err) {
    if (err.name !== 'AbortError') error.value = err.message
  } finally {
    loading.value = false
  }
}

function changeYear(event) {
  router.replace({
    name: 'dashboard',
    query: { year: event.target.value },
  })
}

watch(year, load, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>

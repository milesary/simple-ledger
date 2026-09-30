<template>
  <div class="page-container">
    <header class="page-heading">
      <div>
        <p class="eyebrow">预算管理</p>
        <h1>给支出设一条边界</h1>
        <p>按月设置总预算，实时查看使用率和剩余额度。</p>
      </div>
    </header>

    <div v-if="loading" class="loading-panel">
      <LoaderCircle class="spin" :size="24" />
      正在加载预算...
    </div>

    <div v-else-if="error" class="error-panel">
      <CircleAlert :size="22" />
      <span>{{ error }}</span>
      <button class="secondary-button" type="button" @click="load">重试</button>
    </div>

    <template v-else>
      <section class="budget-hero content-card">
        <div>
          <span class="metric-label">{{ data.current_month }} 预算</span>
          <h2 v-if="data.current_budget">
            {{ formatCurrency(data.current_budget.amount) }}
          </h2>
          <h2 v-else class="muted-value">尚未设置</h2>
          <p v-if="data.current_budget">
            已支出 {{ formatCurrency(data.current_expense) }}，剩余
            <strong :class="data.current_budget.remaining < 0 ? 'is-expense' : 'is-income'">
              {{ formatCurrency(data.current_budget.remaining) }}
            </strong>
          </p>
          <p v-else>设置本月预算后，这里会显示使用进度。</p>
        </div>

        <div v-if="data.current_budget" class="budget-hero__progress">
          <strong>{{ Number(data.current_budget.usage_percent).toFixed(1) }}%</strong>
          <div class="progress-track">
            <span
              :class="{ over: data.current_budget.usage_percent > 100 }"
              :style="{ width: `${Math.min(data.current_budget.usage_percent, 100)}%` }"
            ></span>
          </div>
          <small>预算使用率</small>
        </div>
      </section>

      <section class="budget-layout">
        <form class="content-card form-card" @submit.prevent="save">
          <div class="card-heading">
            <div>
              <span>{{ data.current_budget ? '调整额度' : '设置额度' }}</span>
              <h2>{{ data.current_month }} 月预算</h2>
            </div>
          </div>

          <label class="field">
            <span>预算金额 *</span>
            <div class="money-input">
              <b>¥</b>
              <input
                v-model="amount"
                type="number"
                min="0.01"
                step="0.01"
                placeholder="0.00"
                required
              />
            </div>
            <small>只统计当月支出，预算不会影响收入。</small>
          </label>

          <p v-if="saveError" class="form-message form-message--error">
            {{ saveError }}
          </p>

          <button class="primary-button primary-button--wide" type="submit" :disabled="saving">
            <LoaderCircle v-if="saving" class="spin" :size="18" />
            {{ saving ? '保存中...' : data.current_budget ? '更新预算' : '保存预算' }}
          </button>
        </form>

        <article class="content-card content-card--wide">
          <div class="card-heading">
            <div>
              <span>历史记录</span>
              <h2>预算执行情况</h2>
            </div>
          </div>

          <div v-if="data.history.length" class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>月份</th>
                  <th class="align-right">预算</th>
                  <th class="align-right">已支出</th>
                  <th class="align-right">使用率</th>
                  <th class="align-right">剩余</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in data.history" :key="item.month">
                  <td class="nowrap">{{ item.month }}</td>
                  <td class="align-right">{{ formatCurrency(item.amount) }}</td>
                  <td class="align-right is-expense">{{ formatCurrency(item.expense) }}</td>
                  <td
                    class="align-right amount-cell"
                    :class="{ 'is-expense': item.usage_percent > 100 }"
                  >
                    {{ Number(item.usage_percent).toFixed(1) }}%
                  </td>
                  <td
                    class="align-right amount-cell"
                    :class="item.remaining < 0 ? 'is-expense' : 'is-income'"
                  >
                    {{ formatCurrency(item.remaining) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <EmptyState
            v-else
            title="暂无历史预算"
            description="保存本月预算后，会在这里形成按月记录。"
          />
        </article>
      </section>

      <section class="content-card category-budget-card">
        <div class="card-heading">
          <div>
            <span>分类控制</span>
            <h2>{{ data.current_month }} 分类预算</h2>
          </div>
          <small>为餐饮、交通等分类单独设置上限</small>
        </div>

        <div class="table-scroll">
          <table class="data-table category-budget-table">
            <thead>
              <tr>
                <th>分类</th>
                <th class="align-right">本月支出</th>
                <th>分类预算</th>
                <th class="align-right">使用率</th>
                <th class="align-right">剩余</th>
                <th class="align-center">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in data.category_budgets" :key="item.category_id">
                <td>
                  <span class="category-badge">{{ item.category_name }}</span>
                </td>
                <td class="align-right is-expense">{{ formatCurrency(item.expense) }}</td>
                <td>
                  <div class="category-budget-input">
                    <span>¥</span>
                    <input
                      v-model="categoryAmounts[item.category_id]"
                      type="number"
                      min="0.01"
                      step="0.01"
                      placeholder="未设置"
                    />
                  </div>
                </td>
                <td
                  class="align-right amount-cell"
                  :class="{ 'is-expense': item.usage_percent > 100 }"
                >
                  {{ item.amount ? `${Number(item.usage_percent).toFixed(1)}%` : '-' }}
                </td>
                <td
                  class="align-right amount-cell"
                  :class="item.remaining < 0 ? 'is-expense' : 'is-income'"
                >
                  {{ item.remaining === null ? '-' : formatCurrency(item.remaining) }}
                </td>
                <td>
                  <div class="row-actions">
                    <button
                      class="secondary-button"
                      type="button"
                      :disabled="savingCategoryId === item.category_id"
                      @click="saveCategory(item)"
                    >
                      <LoaderCircle
                        v-if="savingCategoryId === item.category_id"
                        class="spin"
                        :size="15"
                      />
                      <span v-else>保存</span>
                    </button>
                    <button
                      v-if="item.amount"
                      class="icon-button icon-button--danger"
                      type="button"
                      title="删除分类预算"
                      aria-label="删除分类预算"
                      @click="removeCategory(item)"
                    >
                      <Trash2 :size="15" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-if="categoryError" class="form-message form-message--error">
          {{ categoryError }}
        </p>
      </section>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { CircleAlert, LoaderCircle, Trash2 } from 'lucide-vue-next'
import { budgetsApi } from '../api/budgets'
import EmptyState from '../components/EmptyState.vue'
import { formatCurrency } from '../utils/format'

const loading = ref(true)
const error = ref('')
const saving = ref(false)
const saveError = ref('')
const categoryError = ref('')
const savingCategoryId = ref(null)
const amount = ref('')
const categoryAmounts = reactive({})
const data = ref({
  current_month: '',
  current_budget: null,
  current_expense: 0,
  category_budgets: [],
  history: [],
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await budgetsApi.get()
    amount.value = data.value.current_budget
      ? Number(data.value.current_budget.amount).toFixed(2)
      : ''
    Object.keys(categoryAmounts).forEach((key) => delete categoryAmounts[key])
    data.value.category_budgets.forEach((item) => {
      categoryAmounts[item.category_id] = item.amount
        ? Number(item.amount).toFixed(2)
        : ''
    })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function save() {
  const value = Number(amount.value)
  if (!Number.isFinite(value) || value <= 0) {
    saveError.value = '预算金额必须大于 0'
    return
  }

  saving.value = true
  saveError.value = ''
  try {
    const result = await budgetsApi.save({
      month: data.value.current_month,
      amount: value,
    })
    if (!result.success) throw new Error(result.message || '预算保存失败')
    await load()
    amount.value = Number(result.budget.amount).toFixed(2)
  } catch (err) {
    saveError.value = err.message
  } finally {
    saving.value = false
  }
}

async function saveCategory(item) {
  const value = Number(categoryAmounts[item.category_id])
  if (!Number.isFinite(value) || value <= 0) {
    categoryError.value = `请输入“${item.category_name}”的有效预算金额`
    return
  }

  savingCategoryId.value = item.category_id
  categoryError.value = ''
  try {
    await budgetsApi.saveCategory({
      month: data.value.current_month,
      category_id: item.category_id,
      amount: value,
    })
    await load()
  } catch (err) {
    categoryError.value = err.message
  } finally {
    savingCategoryId.value = null
  }
}

async function removeCategory(item) {
  if (!window.confirm(`确定清除“${item.category_name}”的分类预算吗？`)) return
  categoryError.value = ''
  try {
    await budgetsApi.removeCategory({
      month: data.value.current_month,
      categoryId: item.category_id,
    })
    await load()
  } catch (err) {
    categoryError.value = err.message
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
.category-budget-card {
  margin-top: 1rem;
}

.category-budget-table {
  min-width: 860px;
}

.category-budget-input {
  display: grid;
  grid-template-columns: auto minmax(100px, 1fr);
  align-items: center;
  min-width: 150px;
  overflow: hidden;
  background: var(--sl-control-bg);
  border: 1px solid var(--sl-border-strong);
  border-radius: var(--sl-radius-input);
}

.category-budget-input span {
  display: grid;
  align-self: stretch;
  padding: 0 0.55rem;
  color: var(--sl-accent-text);
  background: var(--sl-surface-muted);
  place-items: center;
}

.category-budget-input input {
  width: 100%;
  min-width: 0;
  min-height: 39px;
  padding: 0.45rem 0.6rem;
  border: 0;
  outline: none;
}
</style>

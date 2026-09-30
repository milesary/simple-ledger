<template>
  <div class="page-container">
    <header class="page-heading">
      <div>
        <p class="eyebrow">自动化记账</p>
        <h1>周期流水</h1>
        <p>为工资、房租、订阅和固定还款建立规则，到期后自动生成真实流水。</p>
      </div>
    </header>

    <div v-if="loading" class="loading-panel">
      <LoaderCircle class="spin" :size="24" />
      正在加载周期规则...
    </div>

    <div v-else-if="error" class="error-panel">
      <CircleAlert :size="22" />
      <span>{{ error }}</span>
      <button class="secondary-button" type="button" @click="load">重试</button>
    </div>

    <template v-else>
      <div v-if="generatedCount" class="form-message form-message--success">
        已自动补生成 {{ generatedCount }} 条到期流水。
      </div>

      <section class="recurring-summary content-card">
        <article class="recurring-summary__item">
          <span class="recurring-summary__icon">
            <Repeat2 :size="19" />
          </span>
          <div>
            <small>启用规则</small>
            <strong>{{ activeRuleCount }}</strong>
            <span>共 {{ recurring.length }} 条周期规则</span>
          </div>
        </article>

        <article class="recurring-summary__item">
          <span class="recurring-summary__icon recurring-summary__icon--expense">
            <TrendingDown :size="19" />
          </span>
          <div>
            <small>固定支出</small>
            <strong class="is-expense">{{ expenseRuleCount }}</strong>
            <span>房租、订阅和固定还款</span>
          </div>
        </article>

        <article class="recurring-summary__item">
          <span class="recurring-summary__icon recurring-summary__icon--income">
            <TrendingUp :size="19" />
          </span>
          <div>
            <small>固定收入</small>
            <strong class="is-income">{{ incomeRuleCount }}</strong>
            <span>工资和其他周期收入</span>
          </div>
        </article>
      </section>

      <form class="content-card form-card recurring-editor" @submit.prevent="save">
        <div class="card-heading recurring-editor__heading">
          <div>
            <span>{{ editingId ? '编辑规则' : '新增规则' }}</span>
            <h2>{{ editingId ? '更新周期设置' : '让固定收支自动发生' }}</h2>
          </div>

          <div class="type-toggle">
            <button
              v-for="item in types"
              :key="item.value"
              type="button"
              :class="[item.value, { active: form.type === item.value }]"
              @click="changeType(item.value)"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <div class="recurring-editor__grid">
          <label class="field">
            <span>金额 *</span>
            <div class="money-input">
              <b>¥</b>
              <input
                v-model="form.amount"
                type="number"
                min="0.01"
                step="0.01"
                placeholder="0.00"
                required
              />
            </div>
          </label>

          <label class="field">
            <span>分类 *</span>
            <select v-model="form.category_id" required>
              <option value="">请选择</option>
              <option v-for="item in filteredCategories" :key="item.id" :value="item.id">
                {{ item.name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>账户</span>
            <select v-model="form.account_id">
              <option value="">不关联账户</option>
              <option v-for="account in activeAccounts" :key="account.id" :value="account.id">
                {{ account.name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>支付方式</span>
            <input
              v-model.trim="form.payment_method"
              type="text"
              maxlength="20"
              placeholder="微信、银行卡等"
            />
          </label>

          <label class="field">
            <span>执行频率 *</span>
            <select v-model="form.frequency" required>
              <option v-for="item in frequencies" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>间隔 *</span>
            <input v-model.number="form.interval" type="number" min="1" max="365" required />
          </label>

          <label class="field">
            <span>首次日期 *</span>
            <input v-model="form.start_date" type="date" required />
          </label>

          <label class="field">
            <span>结束日期</span>
            <input v-model="form.end_date" type="date" />
            <small>留空表示长期执行。</small>
          </label>
        </div>

        <label class="field">
          <span>备注</span>
          <input
            v-model.trim="form.note"
            type="text"
            maxlength="200"
            placeholder="如：每月工资、视频会员"
          />
        </label>

        <p v-if="formError" class="form-message form-message--error">
          {{ formError }}
        </p>

        <div class="form-actions">
          <button class="primary-button" type="submit" :disabled="saving">
            <LoaderCircle v-if="saving" class="spin" :size="18" />
            {{ saving ? '保存中...' : editingId ? '保存规则' : '创建规则' }}
          </button>
          <button v-if="editingId" class="secondary-button" type="button" @click="resetForm">
            取消编辑
          </button>
        </div>
      </form>

      <section class="recurring-list-panel">
          <div class="card-heading recurring-list-heading">
            <div>
              <span>周期规则</span>
              <h2>{{ activeRuleCount }} 条正在运行</h2>
            </div>
          </div>

          <div class="recurring-list">
            <article
              v-for="rule in recurring"
              :key="rule.id"
              class="recurring-card content-card"
              :class="{ 'is-paused': !rule.is_active }"
            >
              <div class="recurring-card__head">
                <div>
                  <span class="status-pill" :class="rule.type">
                    {{ rule.type === 'income' ? '收入' : '支出' }}
                  </span>
                  <h2>{{ rule.note || rule.category_name }}</h2>
                </div>
                <strong :class="rule.type === 'income' ? 'is-income' : 'is-expense'">
                  {{ rule.type === 'income' ? '+' : '-' }}{{ formatCurrency(rule.amount) }}
                </strong>
              </div>

              <dl class="recurring-card__meta">
                <div>
                  <dt>分类</dt>
                  <dd>{{ rule.category_name }}</dd>
                </div>
                <div>
                  <dt>账户</dt>
                  <dd>{{ rule.account_name || '不关联' }}</dd>
                </div>
                <div>
                  <dt>频率</dt>
                  <dd>{{ frequencyLabel(rule) }}</dd>
                </div>
                <div>
                  <dt>下次执行</dt>
                  <dd>{{ rule.is_active ? formatDate(rule.next_run_date) : '已暂停' }}</dd>
                </div>
              </dl>

              <div class="recurring-card__actions">
                <button class="secondary-button" type="button" @click="edit(rule)">
                  <Pencil :size="15" />
                  编辑
                </button>
                <button
                  class="secondary-button"
                  type="button"
                  :disabled="togglingId === rule.id"
                  @click="toggle(rule)"
                >
                  <Play v-if="!rule.is_active" :size="15" />
                  <Pause v-else :size="15" />
                  {{ rule.is_active ? '暂停' : '启用' }}
                </button>
                <button
                  class="secondary-button danger-button"
                  type="button"
                  :disabled="deletingId === rule.id"
                  @click="remove(rule)"
                >
                  <Trash2 :size="15" />
                  删除
                </button>
              </div>
            </article>

            <EmptyState
              v-if="!recurring.length"
              class="content-card"
              title="还没有周期规则"
              description="创建规则后，系统会在打开概览或本页面时自动补齐到期流水。"
            />
          </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CircleAlert,
  LoaderCircle,
  Pause,
  Pencil,
  Play,
  Repeat2,
  Trash2,
  TrendingDown,
  TrendingUp,
} from 'lucide-vue-next'
import { accountsApi } from '../api/accounts'
import { recurringApi } from '../api/recurring'
import { transactionsApi } from '../api/transactions'
import EmptyState from '../components/EmptyState.vue'
import { formatCurrency, formatDate, todayString } from '../utils/format'

const frequencies = [
  { value: 'daily', label: '每天 / N 天' },
  { value: 'weekly', label: '每周 / N 周' },
  { value: 'monthly', label: '每月 / N 月' },
  { value: 'yearly', label: '每年 / N 年' },
]
const types = [
  { value: 'expense', label: '固定支出' },
  { value: 'income', label: '固定收入' },
]

const loading = ref(true)
const error = ref('')
const saving = ref(false)
const formError = ref('')
const togglingId = ref(null)
const deletingId = ref(null)
const editingId = ref(null)
const generatedCount = ref(0)
const recurring = ref([])
const categories = ref([])
const accounts = ref([])
const form = reactive({
  type: 'expense',
  amount: '',
  category_id: '',
  account_id: '',
  frequency: 'monthly',
  interval: 1,
  start_date: todayString(),
  end_date: '',
  payment_method: '',
  note: '',
})

const filteredCategories = computed(() =>
  categories.value.filter((item) => item.type === form.type),
)
const activeAccounts = computed(() =>
  accounts.value.filter((account) => !account.is_archived),
)
const activeRuleCount = computed(
  () => recurring.value.filter((rule) => rule.is_active).length,
)
const expenseRuleCount = computed(
  () => recurring.value.filter((rule) => rule.type === 'expense').length,
)
const incomeRuleCount = computed(
  () => recurring.value.filter((rule) => rule.type === 'income').length,
)

function changeType(type) {
  if (form.type === type) return
  form.type = type
  form.category_id = ''
}

function frequencyLabel(rule) {
  const item = frequencies.find((frequency) => frequency.value === rule.frequency)
  const unit = {
    daily: '天',
    weekly: '周',
    monthly: '月',
    yearly: '年',
  }[rule.frequency]
  return `每 ${rule.interval} ${unit}（${item?.label || rule.frequency}）`
}

function resetForm() {
  editingId.value = null
  formError.value = ''
  Object.assign(form, {
    type: 'expense',
    amount: '',
    category_id: '',
    account_id: '',
    frequency: 'monthly',
    interval: 1,
    start_date: todayString(),
    end_date: '',
    payment_method: '',
    note: '',
  })
}

function edit(rule) {
  editingId.value = rule.id
  formError.value = ''
  Object.assign(form, {
    type: rule.type,
    amount: Number(rule.amount).toFixed(2),
    category_id: String(rule.category_id),
    account_id: rule.account_id ? String(rule.account_id) : '',
    frequency: rule.frequency,
    interval: rule.interval,
    start_date: rule.start_date,
    end_date: rule.end_date || '',
    payment_method: rule.payment_method || '',
    note: rule.note || '',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [ruleResult, categoryResult, accountResult] = await Promise.all([
      recurringApi.list(),
      transactionsApi.categories(),
      accountsApi.list(),
    ])
    recurring.value = ruleResult.recurring
    generatedCount.value = ruleResult.generated_count
    categories.value = categoryResult.categories
    accounts.value = accountResult.accounts
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function save() {
  const amount = Number(form.amount)
  if (!Number.isFinite(amount) || amount <= 0) {
    formError.value = '金额必须大于 0'
    return
  }
  if (!form.category_id) {
    formError.value = '请选择分类'
    return
  }
  if (form.end_date && form.end_date < form.start_date) {
    formError.value = '结束日期不能早于开始日期'
    return
  }

  saving.value = true
  formError.value = ''
  try {
    const payload = {
      type: form.type,
      amount,
      category_id: Number(form.category_id),
      account_id: form.account_id ? Number(form.account_id) : null,
      frequency: form.frequency,
      interval: Number(form.interval),
      start_date: form.start_date,
      end_date: form.end_date || null,
      payment_method: form.payment_method || null,
      note: form.note || null,
    }
    if (editingId.value) {
      await recurringApi.update(editingId.value, payload)
    } else {
      await recurringApi.create(payload)
    }
    resetForm()
    await load()
  } catch (err) {
    formError.value = err.message
  } finally {
    saving.value = false
  }
}

async function toggle(rule) {
  togglingId.value = rule.id
  try {
    await recurringApi.toggle(rule.id)
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    togglingId.value = null
  }
}

async function remove(rule) {
  if (!window.confirm(`确定删除“${rule.note || rule.category_name}”周期规则吗？`)) return
  deletingId.value = rule.id
  try {
    await recurringApi.remove(rule.id)
    if (editingId.value === rule.id) resetForm()
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    deletingId.value = null
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
.recurring-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 1rem;
  padding: 1.15rem 1.25rem;
}

.recurring-summary__item {
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 0.25rem 1.2rem;
  gap: 0.8rem;
  border-left: 1px solid var(--sl-border);
}

.recurring-summary__item:first-child {
  padding-left: 0;
  border-left: 0;
}

.recurring-summary__item:last-child {
  padding-right: 0;
}

.recurring-summary__icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  color: var(--sl-accent-text);
  background: var(--sl-accent-soft);
  border-radius: 9px;
  place-items: center;
}

.recurring-summary__icon--expense {
  color: var(--sl-expense);
  background: var(--sl-expense-soft);
}

.recurring-summary__icon--income {
  color: var(--sl-income);
  background: var(--sl-income-soft);
}

.recurring-summary__item > div {
  display: grid;
  min-width: 0;
}

.recurring-summary__item small,
.recurring-summary__item span {
  color: var(--sl-text-muted);
  font-size: 0.7rem;
}

.recurring-summary__item strong {
  color: var(--text-primary);
  font-size: 1.55rem;
  line-height: 1.2;
}

.recurring-editor {
  margin-bottom: 1rem;
}

.recurring-editor__heading {
  align-items: center;
}

.recurring-editor__heading .type-toggle {
  width: min(320px, 100%);
  margin: 0;
}

.recurring-editor__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 1rem;
  gap: 1rem;
}

.recurring-list-panel {
  min-width: 0;
}

.recurring-list-heading {
  margin-bottom: 0.85rem;
  padding-inline: 0.15rem;
}

.recurring-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  min-width: 0;
  gap: 1rem;
}

.recurring-card.is-paused {
  opacity: 0.66;
}

.recurring-card {
  min-width: 0;
  overflow: hidden;
}

.recurring-list > .empty-state {
  min-height: 220px;
  grid-column: 1 / -1;
}

.recurring-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.recurring-card__head > div {
  min-width: 0;
}

.recurring-card__head h2 {
  margin-top: 0.55rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recurring-card__head > strong {
  font-size: 1.05rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.recurring-card__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 1rem 0;
  gap: 0.7rem;
}

.recurring-card__meta > div {
  min-width: 0;
}

.recurring-card__meta dt {
  color: var(--sl-text-subtle);
  font-size: 0.68rem;
}

.recurring-card__meta dd {
  margin: 0.18rem 0 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 0.78rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recurring-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 1080px) {
  .recurring-editor__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .recurring-summary,
  .recurring-editor__grid,
  .recurring-list {
    grid-template-columns: 1fr;
  }

  .recurring-summary__item,
  .recurring-summary__item:first-child {
    padding: 0.8rem 0;
    border-top: 1px solid var(--sl-border);
    border-left: 0;
  }

  .recurring-summary__item:first-child {
    padding-top: 0;
    border-top: 0;
  }

  .recurring-editor__heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .recurring-editor__heading .type-toggle {
    width: 100%;
  }
}
</style>

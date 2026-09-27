<template>
  <div class="page-container">
    <header class="page-heading">
      <div>
        <p class="eyebrow">账户体系</p>
        <h1>钱放在哪里，一目了然</h1>
        <p>统一管理现金、银行卡、信用卡和投资账户，余额会随流水与转账实时变化。</p>
      </div>
      <RouterLink class="secondary-button" :to="{ name: 'transfers' }">
        <ArrowLeftRight :size="17" />
        账户转账
      </RouterLink>
    </header>

    <div v-if="loading" class="loading-panel">
      <LoaderCircle class="spin" :size="24" />
      正在加载账户...
    </div>

    <div v-else-if="error" class="error-panel">
      <CircleAlert :size="22" />
      <span>{{ error }}</span>
      <button class="secondary-button" type="button" @click="load">重试</button>
    </div>

    <template v-else>
      <section class="metric-grid metric-grid--accounts">
        <article class="metric-card metric-card--balance">
          <div class="metric-card__top">
            <span>账户总余额</span>
            <WalletCards :size="19" />
          </div>
          <strong :class="totalBalance >= 0 ? 'is-income' : 'is-expense'">
            {{ formatCurrency(totalBalance) }}
          </strong>
          <small>汇总所有已创建账户的当前余额</small>
        </article>
        <article class="metric-card">
          <div class="metric-card__top">
            <span>可用账户</span>
            <Landmark :size="19" />
          </div>
          <strong>{{ activeAccounts.length }}</strong>
          <small>共 {{ accounts.length }} 个账户</small>
        </article>
      </section>

      <section class="account-workspace">
        <form class="content-card form-card account-form-panel" @submit.prevent="save">
          <div class="card-heading">
            <div>
              <span>{{ editingId ? '编辑账户' : '新增账户' }}</span>
              <h2>{{ editingId ? '更新账户信息' : '建立资金账户' }}</h2>
            </div>
          </div>

          <label class="field">
            <span>账户名称 *</span>
            <input
              v-model.trim="form.name"
              type="text"
              maxlength="50"
              placeholder="如：工资卡、微信零钱"
              required
            />
          </label>

          <label class="field">
            <span>账户类型 *</span>
            <select v-model="form.type" required>
              <option v-for="item in accountTypes" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>初始余额</span>
            <div class="money-input">
              <b>¥</b>
              <input
                v-model="form.initial_balance"
                type="number"
                step="0.01"
                placeholder="0.00"
              />
            </div>
            <small>开始使用简账时该账户已有的余额，可以填写负数。</small>
          </label>

          <p v-if="formError" class="form-message form-message--error">
            {{ formError }}
          </p>

          <div class="form-actions">
            <button class="primary-button" type="submit" :disabled="saving">
              <LoaderCircle v-if="saving" class="spin" :size="18" />
              {{ saving ? '保存中...' : editingId ? '保存账户' : '创建账户' }}
            </button>
            <button
              v-if="editingId"
              class="secondary-button"
              type="button"
              @click="resetForm"
            >
              取消编辑
            </button>
          </div>
        </form>

        <section class="account-list-panel">
          <div class="card-heading account-list-heading">
            <div>
              <span>账户列表</span>
              <h2>{{ accounts.length }} 个资金账户</h2>
            </div>
          </div>

          <div v-if="accounts.length" class="account-grid">
            <article
              v-for="account in accounts"
              :key="account.id"
              class="account-card content-card"
              :class="{ 'is-archived': account.is_archived }"
            >
              <div class="account-card__head">
                <span class="account-icon">
                  <WalletCards :size="20" />
                </span>
                <div>
                  <strong>{{ account.name }}</strong>
                  <span>{{ typeLabel(account.type) }}</span>
                </div>
                <span v-if="account.is_archived" class="status-pill">已归档</span>
              </div>

              <div class="account-card__balance">
                <span>当前余额</span>
                <strong :class="account.balance >= 0 ? 'is-income' : 'is-expense'">
                  {{ formatCurrency(account.balance) }}
                </strong>
              </div>

              <div class="account-card__meta">
                <span>初始余额 {{ formatCurrency(account.initial_balance) }}</span>
              </div>

              <div v-if="!account.is_archived" class="account-card__actions">
                <button class="secondary-button" type="button" @click="edit(account)">
                  <Pencil :size="15" />
                  编辑
                </button>
                <button
                  class="secondary-button danger-button"
                  type="button"
                  :disabled="archivingId === account.id"
                  @click="archive(account)"
                >
                  <Archive :size="15" />
                  归档
                </button>
              </div>
            </article>
          </div>

          <EmptyState
            v-else
            class="content-card"
            title="还没有账户"
            description="先创建工资卡、现金或信用卡账户，之后记账时可以关联余额。"
          />
        </section>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Archive,
  ArrowLeftRight,
  CircleAlert,
  Landmark,
  LoaderCircle,
  Pencil,
  WalletCards,
} from 'lucide-vue-next'
import { accountsApi } from '../api/accounts'
import EmptyState from '../components/EmptyState.vue'
import { formatCurrency } from '../utils/format'

const accountTypes = [
  { value: 'cash', label: '现金' },
  { value: 'bank', label: '银行卡' },
  { value: 'credit', label: '信用卡' },
  { value: 'investment', label: '投资账户' },
  { value: 'other', label: '其他' },
]

const loading = ref(true)
const error = ref('')
const saving = ref(false)
const formError = ref('')
const archivingId = ref(null)
const editingId = ref(null)
const totalBalance = ref(0)
const accounts = ref([])
const form = reactive({
  name: '',
  type: 'bank',
  initial_balance: '0.00',
})

const activeAccounts = computed(() =>
  accounts.value.filter((account) => !account.is_archived),
)

function typeLabel(type) {
  return accountTypes.find((item) => item.value === type)?.label || '其他'
}

function resetForm() {
  editingId.value = null
  formError.value = ''
  Object.assign(form, {
    name: '',
    type: 'bank',
    initial_balance: '0.00',
  })
}

function edit(account) {
  editingId.value = account.id
  formError.value = ''
  Object.assign(form, {
    name: account.name,
    type: account.type,
    initial_balance: Number(account.initial_balance).toFixed(2),
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await accountsApi.list()
    accounts.value = result.accounts
    totalBalance.value = result.total_balance
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function save() {
  const initialBalance = Number(form.initial_balance || 0)
  if (!form.name) {
    formError.value = '请输入账户名称'
    return
  }
  if (!Number.isFinite(initialBalance)) {
    formError.value = '初始余额格式不正确'
    return
  }

  saving.value = true
  formError.value = ''
  try {
    const payload = {
      name: form.name,
      type: form.type,
      initial_balance: initialBalance,
    }
    if (editingId.value) {
      await accountsApi.update(editingId.value, payload)
    } else {
      await accountsApi.create(payload)
    }
    resetForm()
    await load()
  } catch (err) {
    formError.value = err.message
  } finally {
    saving.value = false
  }
}

async function archive(account) {
  if (!window.confirm(`确定归档“${account.name}”吗？历史流水会继续保留。`)) return
  archivingId.value = account.id
  try {
    await accountsApi.archive(account.id)
    if (editingId.value === account.id) resetForm()
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    archivingId.value = null
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
.metric-grid--accounts {
  grid-template-columns: minmax(0, 1.5fr) minmax(240px, 0.5fr);
}

.account-workspace {
  display: grid;
  grid-template-areas: "list form";
  grid-template-columns: minmax(0, 1.35fr) minmax(290px, 0.65fr);
  align-items: start;
  gap: 1rem;
}

.account-form-panel {
  position: sticky;
  top: 92px;
  grid-area: form;
}

.account-list-panel {
  min-width: 0;
  grid-area: list;
}

.account-list-heading {
  margin-bottom: 0.85rem;
  padding-inline: 0.15rem;
}

.account-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.account-card {
  display: grid;
  gap: 1rem;
}

.account-card.is-archived {
  opacity: 0.65;
}

.account-card__head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.7rem;
}

.account-card__head > div {
  display: grid;
}

.account-card__head strong {
  overflow: hidden;
  color: #315972;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-card__head span {
  color: var(--sl-text-muted);
  font-size: 0.72rem;
}

.account-icon {
  display: grid;
  width: 42px;
  height: 42px;
  color: var(--sl-accent-text);
  background: var(--sl-accent-soft);
  border-radius: 12px;
  place-items: center;
}

.account-card__balance {
  display: grid;
  gap: 0.2rem;
}

.account-card__balance span,
.account-card__meta {
  color: var(--sl-text-muted);
  font-size: 0.76rem;
}

.account-card__balance strong {
  color: #2d5c78;
  font-size: 1.55rem;
  font-variant-numeric: tabular-nums;
}

.account-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 1080px) {
  .account-workspace {
    grid-template-areas:
      "list"
      "form";
    grid-template-columns: 1fr;
  }

  .account-form-panel {
    position: static;
  }
}

@media (max-width: 680px) {
  .metric-grid--accounts,
  .account-grid {
    grid-template-columns: 1fr;
  }
}
</style>

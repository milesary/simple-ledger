<template>
  <div class="page-container">
    <header class="page-heading">
      <div>
        <p class="eyebrow">资金调拨</p>
        <h1>账户间转账</h1>
        <p>转账只改变账户余额，不会计入收入、支出或消费预算。</p>
      </div>
      <RouterLink class="secondary-button" :to="{ name: 'accounts' }">
        <WalletCards :size="17" />
        管理账户
      </RouterLink>
    </header>

    <div v-if="loading" class="loading-panel">
      <LoaderCircle class="spin" :size="24" />
      正在加载转账记录...
    </div>

    <div v-else-if="error" class="error-panel">
      <CircleAlert :size="22" />
      <span>{{ error }}</span>
      <button class="secondary-button" type="button" @click="load">重试</button>
    </div>

    <template v-else>
      <section class="transfer-layout">
        <form class="content-card form-card" @submit.prevent="save">
          <div class="card-heading">
            <div>
              <span>{{ editingId ? '编辑转账' : '记录转账' }}</span>
              <h2>{{ editingId ? '更新资金调拨' : '从一个账户转到另一个账户' }}</h2>
            </div>
          </div>

          <div class="form-grid">
            <label class="field">
              <span>转出账户 *</span>
              <select v-model="form.from_account_id" required>
                <option value="">请选择</option>
                <option v-for="account in activeAccounts" :key="account.id" :value="account.id">
                  {{ account.name }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>转入账户 *</span>
              <select v-model="form.to_account_id" required>
                <option value="">请选择</option>
                <option
                  v-for="account in targetAccounts"
                  :key="account.id"
                  :value="account.id"
                >
                  {{ account.name }}
                </option>
              </select>
            </label>
          </div>

          <div class="form-grid">
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
              <span>日期 *</span>
              <input v-model="form.occurred_on" type="date" required />
            </label>
          </div>

          <label class="field">
            <span>备注</span>
            <input
              v-model.trim="form.note"
              type="text"
              maxlength="200"
              placeholder="如：信用卡还款、补充零钱"
            />
          </label>

          <p v-if="formError" class="form-message form-message--error">
            {{ formError }}
          </p>

          <div class="form-actions">
            <button class="primary-button" type="submit" :disabled="saving || activeAccounts.length < 2">
              <LoaderCircle v-if="saving" class="spin" :size="18" />
              {{ saving ? '保存中...' : editingId ? '保存转账' : '确认转账' }}
            </button>
            <button v-if="editingId" class="secondary-button" type="button" @click="resetForm">
              取消编辑
            </button>
          </div>
        </form>

        <article class="content-card content-card--wide">
          <div class="card-heading card-heading--table">
            <div>
              <span>转账历史</span>
              <h2>{{ transfers.length }} 笔记录</h2>
            </div>
          </div>

          <div v-if="transfers.length" class="table-scroll">
            <table class="data-table transfer-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>资金流向</th>
                  <th>备注</th>
                  <th class="align-right">金额</th>
                  <th class="align-center">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in transfers" :key="item.id">
                  <td class="nowrap">{{ formatDate(item.occurred_on) }}</td>
                  <td>
                    <span class="transfer-route">
                      {{ item.from_account_name }}
                      <ArrowRight :size="14" />
                      {{ item.to_account_name }}
                    </span>
                  </td>
                  <td class="table-note">{{ item.note || '-' }}</td>
                  <td class="align-right amount-cell">{{ formatCurrency(item.amount) }}</td>
                  <td>
                    <div class="row-actions">
                      <button
                        class="icon-button"
                        type="button"
                        title="编辑"
                        aria-label="编辑转账"
                        @click="edit(item)"
                      >
                        <Pencil :size="16" />
                      </button>
                      <button
                        class="icon-button icon-button--danger"
                        type="button"
                        title="删除"
                        aria-label="删除转账"
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
            title="还没有转账记录"
            description="当资金在银行卡、现金或投资账户之间移动时，可以在这里记录。"
          >
            <RouterLink v-if="activeAccounts.length < 2" class="primary-button" :to="{ name: 'accounts' }">
              先创建至少两个账户
            </RouterLink>
          </EmptyState>
        </article>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowRight,
  CircleAlert,
  LoaderCircle,
  Pencil,
  Trash2,
  WalletCards,
} from 'lucide-vue-next'
import { accountsApi } from '../api/accounts'
import { transfersApi } from '../api/transfers'
import EmptyState from '../components/EmptyState.vue'
import { formatCurrency, formatDate, todayString } from '../utils/format'

const loading = ref(true)
const error = ref('')
const saving = ref(false)
const formError = ref('')
const deletingId = ref(null)
const editingId = ref(null)
const accounts = ref([])
const transfers = ref([])
const form = reactive({
  from_account_id: '',
  to_account_id: '',
  amount: '',
  occurred_on: todayString(),
  note: '',
})

const activeAccounts = computed(() =>
  accounts.value.filter((account) => !account.is_archived),
)
const targetAccounts = computed(() =>
  activeAccounts.value.filter(
    (account) => String(account.id) !== String(form.from_account_id),
  ),
)

function resetForm() {
  editingId.value = null
  formError.value = ''
  Object.assign(form, {
    from_account_id: '',
    to_account_id: '',
    amount: '',
    occurred_on: todayString(),
    note: '',
  })
}

function edit(item) {
  editingId.value = item.id
  Object.assign(form, {
    from_account_id: String(item.from_account_id),
    to_account_id: String(item.to_account_id),
    amount: Number(item.amount).toFixed(2),
    occurred_on: item.occurred_on,
    note: item.note || '',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [accountResult, transferResult] = await Promise.all([
      accountsApi.list(),
      transfersApi.list(),
    ])
    accounts.value = accountResult.accounts
    transfers.value = transferResult.transfers
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function save() {
  const amount = Number(form.amount)
  if (!form.from_account_id || !form.to_account_id) {
    formError.value = '请选择转出和转入账户'
    return
  }
  if (String(form.from_account_id) === String(form.to_account_id)) {
    formError.value = '转出账户和转入账户不能相同'
    return
  }
  if (!Number.isFinite(amount) || amount <= 0) {
    formError.value = '转账金额必须大于 0'
    return
  }

  saving.value = true
  formError.value = ''
  try {
    const payload = {
      from_account_id: Number(form.from_account_id),
      to_account_id: Number(form.to_account_id),
      amount,
      occurred_on: form.occurred_on,
      note: form.note || null,
    }
    if (editingId.value) {
      await transfersApi.update(editingId.value, payload)
    } else {
      await transfersApi.create(payload)
    }
    resetForm()
    await load()
  } catch (err) {
    formError.value = err.message
  } finally {
    saving.value = false
  }
}

async function remove(item) {
  if (!window.confirm(`确定删除这笔 ${formatCurrency(item.amount)} 的转账吗？`)) return
  deletingId.value = item.id
  try {
    await transfersApi.remove(item.id)
    if (editingId.value === item.id) resetForm()
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
.transfer-layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.75fr) minmax(0, 1.25fr);
  align-items: start;
  gap: 1rem;
}

.transfer-table {
  min-width: 760px;
}

.transfer-route {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-primary);
  font-weight: 700;
  white-space: nowrap;
}

@media (max-width: 1080px) {
  .transfer-layout {
    grid-template-columns: 1fr;
  }
}
</style>

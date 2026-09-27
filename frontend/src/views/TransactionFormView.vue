<template>
  <div class="page-container page-container--narrow">
    <button class="back-link" type="button" @click="router.back()">
      <ArrowLeft :size="17" />
      返回
    </button>

    <header class="page-heading page-heading--compact">
      <div>
        <p class="eyebrow">{{ isEditing ? '更新记录' : '新增记录' }}</p>
        <h1>{{ isEditing ? '编辑流水' : '记一笔' }}</h1>
        <p>填写金额、分类和日期，收入与支出会分别统计。</p>
      </div>
    </header>

    <div v-if="loading" class="loading-panel">
      <LoaderCircle class="spin" :size="24" />
      正在加载流水...
    </div>

    <div v-else-if="loadError" class="error-panel">
      <CircleAlert :size="22" />
      <span>{{ loadError }}</span>
      <RouterLink class="secondary-button" :to="{ name: 'transactions' }">
        返回列表
      </RouterLink>
    </div>

    <form v-else class="content-card form-card" @submit.prevent="submit">
      <div class="type-toggle" role="radiogroup" aria-label="收支类型">
        <button
          v-for="item in types"
          :key="item.value"
          type="button"
          role="radio"
          :aria-checked="form.type === item.value"
          :class="[item.value, { active: form.type === item.value }]"
          @click="changeType(item.value)"
        >
          {{ item.label }}
        </button>
      </div>

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
        <small>金额必须大于 0，最多保留两位小数。</small>
      </label>

      <label class="field">
        <span>分类 *</span>
        <select v-model="form.category_id" required>
          <option value="">请选择分类</option>
          <option v-for="item in filteredCategories" :key="item.id" :value="item.id">
            {{ item.name }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>资金账户</span>
        <select v-model="form.account_id">
          <option value="">不关联账户</option>
          <option v-for="account in accounts" :key="account.id" :value="account.id">
            {{ account.name }}{{ account.is_archived ? '（已归档）' : '' }}
          </option>
        </select>
        <small>关联账户后，余额会随这笔流水同步变化。</small>
      </label>

      <div class="form-grid">
        <label class="field">
          <span>日期 *</span>
          <input v-model="form.occurred_on" type="date" required />
        </label>

        <label class="field">
          <span>支付方式</span>
          <input
            v-model.trim="form.payment_method"
            type="text"
            maxlength="20"
            placeholder="微信、支付宝、银行卡"
          />
        </label>
      </div>

      <label class="field">
        <span>备注</span>
        <textarea
          v-model.trim="form.note"
          rows="3"
          maxlength="200"
          placeholder="可选，最多 200 字"
        ></textarea>
      </label>

      <p v-if="submitError" class="form-message form-message--error">
        {{ submitError }}
      </p>

      <div class="form-actions">
        <button class="primary-button" type="submit" :disabled="submitting">
          <LoaderCircle v-if="submitting" class="spin" :size="18" />
          {{ submitting ? '保存中...' : '保存流水' }}
        </button>
        <RouterLink class="secondary-button" :to="{ name: 'transactions' }">
          取消
        </RouterLink>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CircleAlert, LoaderCircle } from 'lucide-vue-next'
import { accountsApi } from '../api/accounts'
import { transactionsApi } from '../api/transactions'
import { todayString } from '../utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const loadError = ref('')
const submitting = ref(false)
const submitError = ref('')
const categories = ref([])
const accounts = ref([])
const types = [
  { value: 'expense', label: '支出' },
  { value: 'income', label: '收入' },
]

const form = reactive({
  type: 'expense',
  amount: '',
  category_id: '',
  account_id: '',
  occurred_on: todayString(),
  payment_method: '',
  note: '',
})

const isEditing = computed(() => Boolean(route.params.id))
const filteredCategories = computed(() =>
  categories.value.filter((item) => item.type === form.type),
)

function changeType(type) {
  if (form.type === type) return
  form.type = type
  form.category_id = ''
}

function payload() {
  return {
    type: form.type,
    amount: form.amount,
    category_id: Number(form.category_id),
    account_id: form.account_id ? Number(form.account_id) : null,
    occurred_on: form.occurred_on,
    payment_method: form.payment_method || null,
    note: form.note || null,
  }
}

async function submit() {
  const amount = Number(form.amount)
  if (!Number.isFinite(amount) || amount <= 0) {
    submitError.value = '金额必须大于 0'
    return
  }
  if (!form.category_id) {
    submitError.value = '请选择分类'
    return
  }

  submitting.value = true
  submitError.value = ''
  try {
    if (isEditing.value) {
      await transactionsApi.update(route.params.id, payload())
    } else {
      await transactionsApi.create(payload())
    }
    router.push({ name: 'transactions' })
  } catch (err) {
    submitError.value = err.message
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  loading.value = true
  loadError.value = ''
  try {
    const requests = [transactionsApi.categories(), accountsApi.list()]
    if (isEditing.value) requests.push(transactionsApi.get(route.params.id))
    const [categoryResult, accountResult, transactionResult] = await Promise.all(requests)
    categories.value = categoryResult.categories
    accounts.value = accountResult.accounts.filter(
      (account) =>
        !account.is_archived ||
        String(account.id) === String(transactionResult?.transaction?.account_id),
    )

    if (transactionResult?.transaction) {
      const item = transactionResult.transaction
      Object.assign(form, {
        type: item.type,
        amount: Number(item.amount).toFixed(2),
        category_id: String(item.category_id),
        account_id: item.account_id ? String(item.account_id) : '',
        occurred_on: item.occurred_on,
        payment_method: item.payment_method || '',
        note: item.note || '',
      })
    }
  } catch (err) {
    loadError.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

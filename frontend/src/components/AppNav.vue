<template>
  <button
    v-if="open"
    class="nav-backdrop"
    type="button"
    aria-label="关闭导航菜单"
    @click="emit('close')"
  ></button>

  <aside class="app-nav-sidebar" :class="{ 'is-open': open }">
    <div class="app-nav-sidebar__inner">
      <button
        class="nav-sidebar-close"
        type="button"
        aria-label="关闭导航菜单"
        @click="emit('close')"
      >
        <X :size="20" />
      </button>

      <nav class="app-nav-sidebar__nav" aria-label="主导航">
        <RouterLink
          v-for="item in navigation"
          :key="item.name"
          class="app-nav-sidebar__link"
          :to="{ name: item.name }"
          @click="emit('close')"
        >
          <LayoutDashboard v-if="item.name === 'dashboard'" :size="18" />
          <ReceiptText v-else-if="item.name === 'transactions'" :size="18" />
          <WalletCards v-else-if="item.name === 'accounts'" :size="18" />
          <ArrowLeftRight v-else-if="item.name === 'transfers'" :size="18" />
          <Repeat2 v-else-if="item.name === 'recurring'" :size="18" />
          <PiggyBank v-else-if="item.name === 'budgets'" :size="18" />
          <Upload v-else :size="18" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </div>
  </aside>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import {
  ArrowLeftRight,
  LayoutDashboard,
  PiggyBank,
  ReceiptText,
  Repeat2,
  Upload,
  WalletCards,
  X,
} from 'lucide-vue-next'

defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close'])

const navigation = [
  { name: 'dashboard', label: '概览' },
  { name: 'transactions', label: '流水' },
  { name: 'accounts', label: '账户' },
  { name: 'transfers', label: '转账' },
  { name: 'recurring', label: '周期' },
  { name: 'budgets', label: '预算' },
  { name: 'imports', label: '导入' },
]
</script>

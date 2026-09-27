<template>
  <div class="trend-chart">
    <div v-if="!trend.length" class="trend-chart__empty">暂无趋势数据</div>
    <div v-else class="trend-chart__scroll">
      <div class="trend-chart__plot">
        <div
          v-for="item in trend"
          :key="item.month"
          class="trend-chart__group"
        >
          <div class="trend-chart__bars">
            <span
              class="trend-chart__bar trend-chart__bar--income"
              :style="{ height: barHeight(item.income) }"
              :title="`收入 ${formatCurrency(item.income)}`"
            ></span>
            <span
              class="trend-chart__bar trend-chart__bar--expense"
              :style="{ height: barHeight(item.expense) }"
              :title="`支出 ${formatCurrency(item.expense)}`"
            ></span>
          </div>
          <span class="trend-chart__label">{{ item.month }} 月</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatCurrency } from '../utils/format'

const props = defineProps({
  trend: {
    type: Array,
    default: () => [],
  },
})

const maxValue = computed(() => {
  const values = props.trend.flatMap((item) => [
    Number(item.income) || 0,
    Number(item.expense) || 0,
  ])
  return Math.max(...values, 0)
})

function barHeight(value) {
  if (!maxValue.value) return '3%'
  return `${Math.max((Number(value) / maxValue.value) * 100, 3)}%`
}
</script>

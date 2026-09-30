<template>
  <div class="category-donut">
    <div class="category-donut__visual" :style="{ background: gradient }">
      <div class="category-donut__center">
        <span>支出</span>
        <strong>{{ formatCurrency(total) }}</strong>
      </div>
    </div>

    <div v-if="categories.length" class="category-donut__legend">
      <div
        v-for="(item, index) in categories"
        :key="item.name"
        class="category-donut__legend-item"
      >
        <span
          class="category-donut__dot"
          :style="{ background: colors[index % colors.length] }"
        ></span>
        <span>{{ item.name }}</span>
        <strong>{{ percent(item.amount) }}%</strong>
      </div>
    </div>
    <p v-else class="category-donut__empty">本月暂无支出分类数据</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatCurrency } from '../utils/format'

const props = defineProps({
  categories: {
    type: Array,
    default: () => [],
  },
})

// 图表分类色板：限定在浅蓝主色系（sky / blue / teal），不使用紫、粉
const colors = ['#0284c7', '#38bdf8', '#0ea5e9', '#2dd4bf', '#64748b']

const total = computed(() =>
  props.categories.reduce((sum, item) => sum + Number(item.amount || 0), 0),
)

const gradient = computed(() => {
  if (!total.value) return 'conic-gradient(#e0f2fe 0 100%)'

  let start = 0
  const parts = props.categories.map((item, index) => {
    const end = start + (Number(item.amount || 0) / total.value) * 360
    const color = colors[index % colors.length]
    const segment = `${color} ${start}deg ${end}deg`
    start = end
    return segment
  })
  return `conic-gradient(${parts.join(', ')})`
})

function percent(value) {
  if (!total.value) return 0
  return Number(((Number(value || 0) / total.value) * 100).toFixed(1))
}
</script>

<template>
  <div class="empty-state">
    <span class="empty-state__icon">
      <Inbox :size="25" />
    </span>
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>

<script setup>
import { Inbox } from 'lucide-vue-next'

defineProps({
  title: {
    type: String,
    default: '暂无数据',
  },
  description: {
    type: String,
    default: '这里还没有可展示的内容。',
  },
})
</script>

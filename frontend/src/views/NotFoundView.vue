<template>
  <section class="not-found">
    <span class="not-found__mark">404</span>
    <h1>页面不存在</h1>
    <p>你访问的地址没有对应页面，可能已经被移动或删除。</p>
    <RouterLink class="primary-button" :to="{ name: 'dashboard' }">
      返回概览
    </RouterLink>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>

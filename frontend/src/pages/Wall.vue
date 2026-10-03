<template>
  <div class="wall">
    <h1 class="serif">愿望墙</h1>
    <p class="tag">无顶栏 · 瀑布流 · 点卡片认领</p>
    <div class="masonry">
      <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
        <h3>{{ w.title || '（无标题）' }}</h3>
        <p>{{ w.note }}</p>
        <p v-if="w.selected_sku" class="pin-line">
          📌 {{ w.selected_sku.title }}<span v-if="w.selected_sku.estimated_price" class="tag"> · ¥{{ w.selected_sku.estimated_price }}</span>
        </p>
        <p v-else class="tag">🧩 {{ w.sku_count }} 条备选待钉选</p>
        <span class="tag">{{ w.status }} · {{ w.data_quality }}</span>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
onMounted(async () => { rows.value = await api('/wishes') })
</script>

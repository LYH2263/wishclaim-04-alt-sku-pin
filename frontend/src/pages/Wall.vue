<template>
  <div class="wall">
    <h1 class="serif">愿望墙</h1>
    <p class="tag">无顶栏 · 瀑布流 · 点卡片认领</p>
    <div class="masonry">
      <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
        <h3>{{ w.title || '（无标题）' }}</h3>
        <p>{{ w.note }}</p>
        <!-- 拍板：已认领只展示钉选一条；未认领显示备选个数 -->
        <p v-if="w.selected_sku" class="pin">
          📌 {{ w.selected_sku.title }}<span v-if="w.selected_sku.price != null"> · ¥{{ w.selected_sku.price }}</span>
        </p>
        <span class="tag">
          {{ w.status }} · {{ w.data_quality }}
          <template v-if="!w.selected_sku && w.sku_count"> · {{ w.sku_count }} 个备选</template>
        </span>
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

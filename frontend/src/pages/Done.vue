<template>
  <div class="wall">
    <h1 class="serif">已完成</h1>
    <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
      <h3>{{ w.title }}</h3>
      <p v-if="w.selected_sku" class="pin-line">
        📌 {{ w.selected_sku.title }}<span v-if="w.selected_sku.estimated_price" class="tag"> · ¥{{ w.selected_sku.estimated_price }}</span>
      </p>
      <p class="tag">{{ w.claimer }}</p>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
onMounted(async () => { rows.value = await api('/done') })
</script>

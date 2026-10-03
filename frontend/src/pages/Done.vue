<template>
  <div class="wall">
    <h1 class="serif">已完成</h1>
    <article v-for="w in rows" :key="w.id" class="card">
      <h3>{{ w.title }}</h3>
      <p v-if="w.selected_sku" class="pin">
        📌 {{ w.selected_sku.title }}<span v-if="w.selected_sku.price != null"> · ¥{{ w.selected_sku.price }}</span>
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

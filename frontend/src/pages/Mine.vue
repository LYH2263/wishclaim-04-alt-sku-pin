<template>
  <div class="wall">
    <h1 class="serif">我的认领</h1>
    <input v-model="name" @change="load" placeholder="认领人名" />
    <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
      <h3>{{ w.title }}</h3>
      <p v-if="w.selected_sku" class="pin">
        📌 {{ w.selected_sku.title }}<span v-if="w.selected_sku.price != null"> · ¥{{ w.selected_sku.price }}</span>
      </p>
      <span class="tag">{{ w.status }} · 到期 {{ w.expires_at }}</span>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const name = ref('访客')
const rows = ref([])
async function load() { rows.value = await api('/mine?claimer=' + encodeURIComponent(name.value)) }
onMounted(load)
</script>

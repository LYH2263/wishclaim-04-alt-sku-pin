<template>
  <div class="wall">
    <h1 class="serif">发愿望</h1>
    <input v-model="title" placeholder="标题" />
    <textarea v-model="note" rows="4" placeholder="备注" />
    <h3 class="serif">备选 SKU（{{ rows.length }}/5）</h3>
    <p class="tag">挂 2～5 条备选，认领人需钉选其一；全部留空则按单愿望发布。</p>
    <div v-for="(s, i) in rows" :key="i" class="sku-row">
      <input v-model="s.title" :placeholder="'备选 ' + (i + 1) + ' 标题'" />
      <input v-model="s.price" class="sku-price" type="number" min="0" step="1" placeholder="估价" />
      <button v-if="rows.length > 1" class="ghost" @click="rows.splice(i, 1)">删</button>
    </div>
    <button v-if="rows.length < 5" class="ghost" @click="rows.push({ title: '', price: '' })">＋ 加一条备选</button>
    <p v-if="err" class="err">{{ err }}</p>
    <div><button @click="submit">发布</button></div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
const router = useRouter()
const title = ref('')
const note = ref('')
const err = ref('')
const rows = ref([{ title: '', price: '' }, { title: '', price: '' }])
async function submit() {
  err.value = ''
  const skus = rows.value.filter(s => s.title.trim() || String(s.price).trim())
  const body = { title: title.value, note: note.value }
  if (skus.length) {
    body.skus = skus.map(s => ({ title: s.title, price: s.price === '' ? null : Number(s.price) }))
  }
  try {
    const r = await api('/wishes', { method: 'POST', body: JSON.stringify(body) })
    router.push('/wishes/' + r.id)
  } catch (e) { err.value = e.message }
}
</script>

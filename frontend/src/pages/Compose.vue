<template>
  <div class="wall">
    <h1 class="serif">发愿望</h1>
    <input v-model="title" placeholder="愿望标题" />
    <textarea v-model="note" rows="3" placeholder="备注（可选）" />

    <h3 class="serif">备选 SKU（2～5 条，认领时需钉选一条）</h3>
    <div v-for="(s, i) in skus" :key="i" class="sku-row">
      <input v-model="s.title" :placeholder="`备选 ${i + 1} 标题`" />
      <input v-model="s.estimated_price" placeholder="估价" class="sku-price" />
      <button type="button" class="ghost" :disabled="skus.length <= 2" @click="skus.splice(i, 1)">删</button>
    </div>
    <p class="tag">{{ skus.length }} / 5 条（至少 2 条）</p>
    <div style="display:flex;gap:8px">
      <button type="button" class="ghost" :disabled="skus.length >= 5" @click="skus.push({title:'',estimated_price:''})">＋ 加一条</button>
      <button @click="submit">发布</button>
    </div>
    <p v-if="err" class="err">{{ err }}</p>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
const router = useRouter()
const title = ref('')
const note = ref('')
const skus = ref([{ title: '', estimated_price: '' }, { title: '', estimated_price: '' }])
const err = ref('')
const REASONS = {
  sku_count: '备选必须 2～5 条',
  sku_title_missing: '每条备选都要填标题',
  sku_title_long: '备选标题过长（≤80 字）',
  sku_price_bad: '估价格式不对',
  sku_price_long: '估价过长',
}
async function submit() {
  err.value = ''
  if (skus.value.some(s => !s.title.trim())) { err.value = '每条备选都要填标题'; return }
  if (skus.value.length < 2 || skus.value.length > 5) { err.value = '备选必须 2～5 条'; return }
  try {
    const r = await api('/wishes', {
      method: 'POST',
      body: JSON.stringify({
        title: title.value, note: note.value,
        skus: skus.value.map(s => ({ title: s.title.trim(), estimated_price: s.estimated_price.trim() })),
      }),
    })
    router.push('/wishes/' + r.id)
  } catch (e) { err.value = REASONS[e.message] || e.message }
}
</script>

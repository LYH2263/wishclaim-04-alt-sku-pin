<template>
  <div class="wall">
    <h1 class="serif">{{ w.title || '（无标题）' }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>

    <!-- 已钉选：与墙卡一致，只展示钉选一条 -->
    <div v-if="w.selected_sku" class="pinbox">
      📌 已钉选：<b>{{ w.selected_sku.title }}</b>
      <span v-if="w.selected_sku.price != null"> · ¥{{ w.selected_sku.price }}</span>
    </div>

    <!-- 未认领：展开全部备选，认领需显式选中一条 -->
    <div v-else-if="w.skus && w.skus.length">
      <h3 class="serif">备选（{{ w.skus.length }}）</h3>
      <label v-for="s in w.skus" :key="s.idx" class="sku-opt">
        <input v-model.number="pick" type="radio" name="sku" :value="s.idx" />
        <span>{{ s.title }}</span>
        <span class="tag">{{ s.price != null ? '¥' + s.price : '估价未定' }}</span>
      </label>
    </div>
    <p v-else class="err">该愿望没有可认领的备选</p>

    <p v-if="err" class="err">{{ err }}</p>
    <input v-model="claimer" placeholder="你的名字" />
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button @click="claim">认领锁定</button>
      <button class="ghost" @click="release">释放</button>
      <button class="ghost" @click="fulfill">核销完成</button>
      <button class="ghost" @click="toggleEdit">{{ editing ? '收起' : '管理备选' }}</button>
    </div>

    <div v-if="editing" class="editbox">
      <p v-if="w.selected_sku" class="tag">已钉选的快照不受增删影响。</p>
      <div v-for="(s, i) in editRows" :key="i" class="sku-row">
        <input v-model="s.title" :placeholder="'备选 ' + (i + 1) + ' 标题'" />
        <input v-model="s.price" class="sku-price" type="number" min="0" step="1" placeholder="估价" />
        <button v-if="editRows.length > 1" class="ghost" @click="editRows.splice(i, 1)">删</button>
      </div>
      <button v-if="editRows.length < 5" class="ghost" @click="editRows.push({ title: '', price: '' })">＋ 加一条</button>
      <button @click="saveSkus">保存备选</button>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const err = ref('')
const pick = ref(null)
const editing = ref(false)
const editRows = ref([])
async function load() {
  w.value = await api('/wishes/' + props.id)
  const skus = w.value.skus || []
  pick.value = skus.length === 1 ? 0 : null  // 仅一条备选时默认选中
}
async function claim() {
  err.value = ''
  if (pick.value == null && (w.value.skus || []).length > 1) { err.value = '请先选中一条备选'; return }
  try {
    await api('/wishes/' + props.id + '/claim', {
      method: 'POST',
      body: JSON.stringify({ claimer: claimer.value, sku_index: pick.value }),
    })
    await load()
  } catch (e) { err.value = e.message }
}
async function release() {
  err.value=''; try { await api('/wishes/'+props.id+'/release',{method:'POST',body:'{}'}); await load() } catch(e){ err.value=e.message }
}
async function fulfill() {
  err.value=''; try { await api('/wishes/'+props.id+'/fulfill',{method:'POST',body:'{}'}); await load() } catch(e){ err.value=e.message }
}
function toggleEdit() {
  editing.value = !editing.value
  if (!editing.value) return
  const src = (w.value.skus && w.value.skus.length) ? w.value.skus : [{ title: w.value.title || '', price: null }]
  editRows.value = src.map(s => ({ title: s.title, price: s.price == null ? '' : s.price }))
}
async function saveSkus() {
  err.value = ''
  const skus = editRows.value
    .filter(s => s.title.trim() || String(s.price).trim())
    .map(s => ({ title: s.title, price: s.price === '' ? null : Number(s.price) }))
  try {
    await api('/wishes/' + props.id + '/skus', { method: 'PUT', body: JSON.stringify({ skus }) })
    editing.value = false
    await load()
  } catch (e) { err.value = e.message }
}
onMounted(load)
</script>

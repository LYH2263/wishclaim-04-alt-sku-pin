<template>
  <div class="wall">
    <h1 class="serif">{{ w.title }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>

    <!-- 未认领：展开全部备选，必须显式钉选 -->
    <div v-if="w.skus" class="sku-box">
      <h3 class="serif">备选（{{ w.sku_count }} 条）· 请钉选一条再认领</h3>
      <label v-for="(s, i) in w.skus" :key="i" class="sku-option" :class="{on: chosen === i}">
        <input type="radio" name="sku" :value="i" v-model.number="chosen" />
        <span class="sku-title">{{ s.title }}</span>
        <span v-if="s.estimated_price" class="tag">¥{{ s.estimated_price }}</span>
      </label>
    </div>

    <!-- 认领后：只展示钉选一条（与墙卡、我的认领一致） -->
    <div v-else-if="w.selected_sku" class="sku-box pinned">
      <h3 class="serif">已钉选</h3>
      <p class="pin-line">
        📌 {{ w.selected_sku.title }}<span v-if="w.selected_sku.estimated_price" class="tag"> · ¥{{ w.selected_sku.estimated_price }}</span>
      </p>
    </div>

    <p v-if="err" class="err">{{ err }}</p>
    <input v-model="claimer" placeholder="你的名字" />
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button @click="claim">认领锁定</button>
      <button class="ghost" @click="release">释放</button>
      <button class="ghost" @click="fulfill">核销完成</button>
    </div>

    <!-- 发布者管理：增删备选（认领后可改，但不动钉选快照；核销后锁定） -->
    <details class="manage">
      <summary class="tag">发布者管理备选（{{ manage.length }} 条）</summary>
      <p v-if="w.status === 'fulfilled'" class="tag">已核销，备选锁定。</p>
      <template v-else>
        <div v-for="(s, i) in manage" :key="i" class="sku-row">
          <input v-model="s.title" :placeholder="`备选 ${i + 1} 标题`" />
          <input v-model="s.estimated_price" placeholder="估价" class="sku-price" />
          <button type="button" class="ghost" :disabled="manage.length <= 1" @click="manage.splice(i, 1)">删</button>
        </div>
        <div style="display:flex;gap:8px;margin-top:6px">
          <button type="button" class="ghost" :disabled="manage.length >= 5" @click="manage.push({title:'',estimated_price:''})">＋ 加一条</button>
          <button type="button" @click="saveSkus">保存备选</button>
        </div>
        <p class="tag">认领后修改备选不会改变已钉选的那条。</p>
      </template>
    </details>
  </div>
</template>
<script setup>
import { ref, watch } from 'vue'
import { api } from '../api'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const chosen = ref(null)
const manage = ref([])
const err = ref('')
const REASONS = {
  sku_none: '该愿望还没有备选，无法认领',
  sku_selection_required: '请先钉选一条备选',
  sku_index_bad: '钉选的备选不存在，请刷新重试',
  locked: '手慢了，已被别人锁定',
  sku_count: '备选必须 1～5 条',
  sku_title_missing: '每条备选都要填标题',
}

watch(() => w.value.skus, (list) => {
  if (!Array.isArray(list)) return
  // 仅一条备选时默认选中；多条必须显式点选（初始为 null）
  chosen.value = list.length === 1 ? 0 : null
})

async function load() {
  w.value = await api('/wishes/' + props.id)
  try { const m = await api('/wishes/' + props.id + '/skus'); manage.value = m.skus || [] } catch { manage.value = [] }
}
async function claim() {
  err.value = ''
  if (w.value.skus && w.value.skus.length > 1 && chosen.value === null) {
    err.value = '请先钉选一条备选'; return
  }
  const payload = { claimer: claimer.value }
  if (w.value.skus && chosen.value !== null) payload.sku_index = chosen.value
  try {
    await api('/wishes/' + props.id + '/claim', { method: 'POST', body: JSON.stringify(payload) })
    await load()
  } catch (e) { err.value = REASONS[e.message] || e.message }
}
async function release() {
  err.value = ''
  try { await api('/wishes/' + props.id + '/release', { method: 'POST', body: '{}' }); await load() }
  catch (e) { err.value = REASONS[e.message] || e.message }
}
async function fulfill() {
  err.value = ''
  try { await api('/wishes/' + props.id + '/fulfill', { method: 'POST', body: '{}' }); await load() }
  catch (e) { err.value = REASONS[e.message] || e.message }
}
async function saveSkus() {
  err.value = ''
  if (manage.value.length < 1 || manage.value.length > 5) { err.value = '备选必须 1～5 条'; return }
  if (manage.value.some(s => !s.title || !s.title.trim())) { err.value = '每条备选都要填标题'; return }
  try {
    await api('/wishes/' + props.id + '/skus', {
      method: 'PATCH',
      body: JSON.stringify({ skus: manage.value.map(s => ({ title: s.title.trim(), estimated_price: (s.estimated_price || '').trim() })) }),
    })
    await load()
  } catch (e) { err.value = REASONS[e.message] || e.message }
}
load()
</script>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { createHttp } from '@/http'

interface Geofence {
  id: string
  name: string
  vertices: [number, number][]
}

const $q = useQuasar()
const rows = ref<Geofence[]>([])
const form = reactive({
  name: 'Yard',
  vertices: '-24,-47; -24,-46; -23,-46; -23,-47',
})

async function load() {
  const http = await createHttp()
  rows.value = await http.get<Geofence[]>('/geofences')
}

async function create() {
  const vertices = form.vertices.split(';').map((part) => {
    const [lat, lng] = part.split(',').map((item) => Number(item.trim()))
    return [lat, lng] as [number, number]
  })
  const http = await createHttp()
  await http.post('/geofences', { name: form.name, vertices })
  $q.notify({ type: 'positive', message: 'Geofence created' })
  await load()
}

onMounted(() => {
  void load()
})
</script>

<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-3"><q-input v-model="form.name" label="Name" /></div>
      <div class="col-6">
        <q-input v-model="form.vertices" label="Vertices lat,lng; lat,lng; ..." />
      </div>
      <div class="col-2 flex items-end">
        <q-btn color="teal-8" label="Add" @click="create" />
      </div>
    </div>
    <q-table
      title="Geofences"
      :rows="rows"
      :columns="[
        { name: 'name', label: 'Name', field: 'name', align: 'left' },
        { name: 'vertices', label: 'Vertices', field: (row: Geofence) => String(row.vertices.length), align: 'left' },
      ]"
      row-key="id"
    />
  </q-page>
</template>

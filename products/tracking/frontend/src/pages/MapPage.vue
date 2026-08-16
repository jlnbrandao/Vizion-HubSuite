<script setup lang="ts">
import { onMounted, ref, shallowRef } from 'vue'
import L from 'leaflet'
import { createHttp } from '@/http'

interface PositionRow {
  id: string
  device_id: string
  latitude: number
  longitude: number
}

const mapEl = ref<HTMLElement | null>(null)
const map = shallowRef<L.Map | null>(null)
const positions = ref<PositionRow[]>([])

onMounted(async () => {
  if (mapEl.value) {
    map.value = L.map(mapEl.value).setView([-23.55, -46.63], 10)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
    }).addTo(map.value)
  }
  try {
    const http = await createHttp()
    positions.value = await http.get<PositionRow[]>('/positions')
    for (const row of positions.value) {
      L.marker([row.latitude, row.longitude]).addTo(map.value as L.Map)
    }
  } catch {
    positions.value = []
  }
})
</script>

<template>
  <q-page class="q-pa-none">
    <div ref="mapEl" style="height: calc(100vh - 50px); width: 100%" />
  </q-page>
</template>

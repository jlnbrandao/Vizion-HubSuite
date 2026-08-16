<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { createHttp } from '@/http'

interface Device {
  id: string
  imei: string
  name: string
  is_active: boolean
}

const $q = useQuasar()
const rows = ref<Device[]>([])
const form = reactive({ imei: '', name: '' })

async function load() {
  const http = await createHttp()
  rows.value = await http.get<Device[]>('/devices')
}

async function create() {
  const http = await createHttp()
  await http.post('/devices', { ...form })
  form.imei = ''
  form.name = ''
  $q.notify({ type: 'positive', message: 'Device created' })
  await load()
}

onMounted(() => {
  void load()
})
</script>

<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-3"><q-input v-model="form.imei" label="IMEI" /></div>
      <div class="col-4"><q-input v-model="form.name" label="Name" /></div>
      <div class="col-2 flex items-end">
        <q-btn color="teal-8" label="Add" @click="create" />
      </div>
    </div>
    <q-table
      title="Devices"
      :rows="rows"
      :columns="[
        { name: 'name', label: 'Name', field: 'name', align: 'left' },
        { name: 'imei', label: 'IMEI', field: 'imei', align: 'left' },
      ]"
      row-key="id"
    />
  </q-page>
</template>

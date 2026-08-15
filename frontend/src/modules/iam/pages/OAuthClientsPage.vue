<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/services/api'

const clients = ref<Array<{ client_id: string; name: string }>>([])
const name = ref('')
const redirectUri = ref('http://localhost:9000/oauth/callback')
const createdSecret = ref('')

onMounted(async () => {
  const { data } = await api.get('/oauth/clients')
  clients.value = data
})

async function createClient() {
  const { data } = await api.post<{ client_id: string; client_secret: string | null; name: string }>(
    '/oauth/clients',
    { name: name.value, redirect_uris: [redirectUri.value] },
  )
  createdSecret.value = data.client_secret || ''
  clients.value.push({ client_id: data.client_id, name: data.name })
}
</script>

<template>
  <q-page padding>
    <h1 class="text-h5 q-mb-md">OAuth clients</h1>
    <q-input v-model="name" label="Name" class="q-mb-sm" />
    <q-input v-model="redirectUri" label="Redirect URI" class="q-mb-sm" />
    <q-btn color="primary" label="Create client" class="q-mb-md" @click="createClient" />
    <q-banner v-if="createdSecret" class="bg-warning q-mb-md">
      Client secret (shown once): <code>{{ createdSecret }}</code>
    </q-banner>
    <q-list bordered>
      <q-item v-for="c in clients" :key="c.client_id">
        <q-item-section>
          <q-item-label>{{ c.name }}</q-item-label>
          <q-item-label caption>{{ c.client_id }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

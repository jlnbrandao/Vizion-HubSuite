<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()
const form = reactive({ login: 'admin@demo.local', password: 'admin123' })

async function onSubmit() {
  try {
    await auth.login(form.login, form.password)
    await router.replace('/')
  } catch {
    $q.notify({ type: 'negative', message: auth.error || 'Login failed' })
  }
}
</script>

<template>
  <q-layout>
    <q-page class="flex flex-center">
      <q-card class="q-pa-lg" style="min-width: 360px">
        <q-card-section>
          <div class="text-h5">Tracking</div>
          <div class="text-caption text-grey">Standalone product login</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="form.login" label="Email" class="q-mb-md" />
          <q-input v-model="form.password" type="password" label="Password" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn color="teal-8" label="Sign in" :loading="auth.loading" @click="onSubmit" />
        </q-card-actions>
      </q-card>
    </q-page>
  </q-layout>
</template>

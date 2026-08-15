<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const mfaToken = ref(sessionStorage.getItem('vizion_mfa_token') || '')
const code = ref('')
const error = ref('')

async function verify() {
  error.value = ''
  try {
    const { data } = await api.post<{
      access_token: string
      user_id: string
      email: string
      full_name: string
    }>('/auth/mfa/verify', {
      mfa_token: mfaToken.value,
      code: code.value,
    })
    auth.setSession({
      accessToken: data.access_token,
      user: { id: data.user_id, email: data.email, full_name: data.full_name, permissions: [] },
    })
    sessionStorage.removeItem('vizion_mfa_token')
    await auth.hydrateIdentity()
    await router.push('/')
  } catch {
    error.value = 'Invalid MFA code'
  }
}
</script>

<template>
  <!-- Public route: no MainLayout — avoid q-page outside q-page-container -->
  <div class="mfa-challenge-page flex flex-center">
    <q-card style="min-width: 320px">
      <q-card-section>
        <div class="text-h6">Verify MFA</div>
      </q-card-section>
      <q-card-section>
        <q-banner v-if="error" class="bg-negative text-white q-mb-md">{{ error }}</q-banner>
        <q-input v-model="code" label="Authenticator or recovery code" />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn color="primary" label="Verify" @click="verify" />
      </q-card-actions>
    </q-card>
  </div>
</template>

<style scoped>
.mfa-challenge-page {
  min-height: 100vh;
  padding: 24px;
}
</style>

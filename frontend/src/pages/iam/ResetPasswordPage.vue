<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/services/api'

const email = ref('')
const token = ref('')
const password = ref('')
const step = ref<'request' | 'reset'>('request')
const message = ref('')

async function requestReset() {
  await api.post('/auth/forgot-password', { email: email.value })
  message.value = 'If the account exists, a reset token was issued (check server logs in development).'
  step.value = 'reset'
}

async function resetPassword() {
  await api.post('/auth/reset-password', {
    token: token.value,
    new_password: password.value,
  })
  message.value = 'Password updated. You can sign in.'
}
</script>

<template>
  <!-- Public route: no MainLayout — avoid q-page outside q-page-container -->
  <div class="reset-page flex flex-center">
    <q-card style="min-width: 360px">
      <q-card-section>
        <div class="text-h6">Reset password</div>
      </q-card-section>
      <q-card-section>
        <q-banner v-if="message" class="bg-info text-white q-mb-md">{{ message }}</q-banner>
        <template v-if="step === 'request'">
          <q-input v-model="email" label="Email" class="q-mb-md" />
          <q-btn color="primary" label="Send reset" @click="requestReset" />
        </template>
        <template v-else>
          <q-input v-model="token" label="Reset token" class="q-mb-sm" />
          <q-input v-model="password" type="password" label="New password" class="q-mb-md" />
          <q-btn color="primary" label="Update password" @click="resetPassword" />
        </template>
      </q-card-section>
    </q-card>
  </div>
</template>

<style scoped>
.reset-page {
  min-height: 100vh;
  padding: 24px;
}
</style>

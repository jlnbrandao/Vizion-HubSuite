<script setup lang="ts">
import { ref } from 'vue'
import QRCode from 'qrcode'
import { api } from '@/services/api'

const methodId = ref('')
const secret = ref('')
const otpauth = ref('')
const qrDataUrl = ref('')
const code = ref('')
const recoveryCodes = ref<string[]>([])
const message = ref('')
const error = ref('')
const enrolling = ref(false)
const confirming = ref(false)

async function enroll() {
  error.value = ''
  message.value = ''
  recoveryCodes.value = []
  enrolling.value = true
  try {
    const { data } = await api.post<{ method_id: string; secret: string; otpauth_uri: string }>(
      '/auth/mfa/totp/enroll',
    )
    methodId.value = data.method_id
    secret.value = data.secret
    otpauth.value = data.otpauth_uri
    qrDataUrl.value = await QRCode.toDataURL(data.otpauth_uri, {
      width: 240,
      margin: 2,
      errorCorrectionLevel: 'M',
    })
  } catch {
    error.value = 'Failed to start TOTP enrollment'
    qrDataUrl.value = ''
  } finally {
    enrolling.value = false
  }
}

async function confirm() {
  error.value = ''
  confirming.value = true
  try {
    const { data } = await api.post<{ recovery_codes: string[] }>('/auth/mfa/totp/confirm', {
      method_id: methodId.value,
      code: code.value,
    })
    recoveryCodes.value = data.recovery_codes
    message.value = 'MFA confirmed. Store recovery codes safely.'
  } catch {
    error.value = 'Invalid authenticator code'
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <q-page padding>
    <h1 class="text-h5 q-mb-md">Multi-factor authentication</h1>
    <p class="text-body2 text-grey-8 q-mb-md">
      Scan the QR code with Google Authenticator, Authy, or another TOTP app.
    </p>

    <q-banner v-if="error" class="bg-negative text-white q-mb-md">{{ error }}</q-banner>
    <q-banner v-if="message" class="bg-positive text-white q-mb-md">{{ message }}</q-banner>

    <q-btn
      color="primary"
      label="Enroll TOTP"
      class="q-mb-md"
      :loading="enrolling"
      @click="enroll"
    />

    <div v-if="secret" class="mfa-enroll q-mb-md">
      <div v-if="qrDataUrl" class="mfa-enroll__qr q-mb-md">
        <img :src="qrDataUrl" alt="TOTP QR code" width="240" height="240" />
      </div>

      <p class="text-caption text-grey-7 q-mb-xs">Or enter this secret manually:</p>
      <p class="mfa-enroll__secret q-mb-md"><code>{{ secret }}</code></p>

      <q-input
        v-model="code"
        label="Authenticator code"
        class="q-mb-sm"
        maxlength="8"
        outlined
        dense
      />
      <q-btn
        color="secondary"
        label="Confirm"
        :loading="confirming"
        :disable="!code.trim()"
        @click="confirm"
      />
    </div>

    <div v-if="recoveryCodes.length" class="mfa-recovery">
      <div class="text-subtitle2 q-mb-sm">Recovery codes</div>
      <ul>
        <li v-for="c in recoveryCodes" :key="c"><code>{{ c }}</code></li>
      </ul>
    </div>
  </q-page>
</template>

<style scoped>
.mfa-enroll__qr {
  display: inline-block;
  padding: 12px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 8px;
}

.mfa-enroll__secret code {
  word-break: break-all;
  font-size: 0.95rem;
}

.mfa-recovery ul {
  margin: 0;
  padding-left: 1.25rem;
  font-family: ui-monospace, monospace;
}
</style>

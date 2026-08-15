<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { useNavigationStore } from '@/stores/navigation'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const auth = useAuthStore()
const dashboard = useDashboardStore()
const navigation = useNavigationStore()
const router = useRouter()
const $q = useQuasar()

const isSigningOut = ref(false)
const showLogoutConfirmModal = ref(false)

const showModal = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const userDisplayName = computed(() => auth.user?.fullName || 'User')
const userEmail = computed(() => auth.user?.email || 'email@example.com')
const userRoles = computed(() => auth.user?.roleNames.join(' · ') || 'no role')

const userAvatarUrl = computed(() => {
  const seed = encodeURIComponent(userEmail.value)
  return `https://api.dicebear.com/9.x/initials/svg?seed=${seed}&backgroundColor=1e40af&textColor=ffffff`
})

function handleSignOut() {
  showLogoutConfirmModal.value = true
}

async function confirmLogout() {
  showLogoutConfirmModal.value = false
  isSigningOut.value = true
  try {
    showModal.value = false
    await auth.logout()
    dashboard.clear()
    navigation.clear()
    await router.push({ name: 'login' })
    $q.notify({ type: 'positive', message: 'Signed out' })
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to sign out' })
    await router.push({ name: 'login' })
  } finally {
    isSigningOut.value = false
  }
}

function handleViewAccount(event: Event) {
  event.preventDefault()
  showModal.value = false
  void router.push({ name: 'account-profile' })
}

function handleSignInDifferent(event: Event) {
  event.preventDefault()
  $q.dialog({
    title: 'Switch account',
    message: 'Do you want to sign out and sign in with another account?',
    cancel: { label: 'Cancel', flat: true },
    ok: { label: 'Yes', color: 'primary' },
  }).onOk(() => {
    handleSignOut()
  })
}
</script>

<template>
  <q-dialog
    v-model="showModal"
    class="account-modal"
  >
    <q-card
      class="account-modal__card"
      role="dialog"
      aria-labelledby="account-modal-title"
      aria-modal="true"
    >
      <div class="account-modal__header">
        <q-btn
          flat
          dense
          no-caps
          class="account-modal__sign-out"
          :loading="isSigningOut"
          :disable="isSigningOut"
          aria-label="Sign out"
          @click="handleSignOut"
        >
          <q-icon
            name="logout"
            size="16px"
            class="q-mr-xs"
          />
          Sign out
        </q-btn>
      </div>

      <q-card-section class="account-modal__body">
        <div class="account-modal__profile">
          <div class="account-modal__avatar-wrap">
            <img
              class="account-modal__avatar"
              width="82"
              height="82"
              :src="userAvatarUrl"
              alt="Avatar"
            >
          </div>
          <div class="account-modal__info">
            <h6 id="account-modal-title">
              {{ userDisplayName }}
            </h6>
            <p :title="userEmail">
              {{ userEmail }}
            </p>
            <small>{{ userRoles }}</small>
            <q-btn
              flat
              dense
              no-caps
              class="account-modal__link"
              aria-label="View account"
              @click="handleViewAccount"
            >
              View account
            </q-btn>
          </div>
        </div>
      </q-card-section>

      <q-card-actions class="account-modal__footer">
        <q-icon
          name="swap_horiz"
          color="primary"
          size="18px"
        />
        <q-btn
          flat
          dense
          no-caps
          class="account-modal__link"
          aria-label="Sign in with another account"
          @click="handleSignInDifferent"
        >
          Sign in with another account
        </q-btn>
      </q-card-actions>
    </q-card>

    <q-dialog
      v-model="showLogoutConfirmModal"
      persistent
    >
      <q-card
        class="q-pa-md"
        style="min-width: 360px; max-width: 480px"
      >
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6 text-weight-bold row items-center">
            <q-icon
              name="logout"
              size="24px"
              class="q-mr-sm text-negative"
            />
            Confirm sign out
          </div>
          <q-space />
          <q-btn
            icon="close"
            flat
            round
            dense
            v-close-popup
            @click="showLogoutConfirmModal = false"
          />
        </q-card-section>

        <q-card-section class="q-pt-md">
          <div class="text-body1 q-mb-sm">
            Are you sure you want to end this session?
          </div>
          <div class="text-body2 text-grey-7">
            You will be redirected to the login screen.
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            flat
            label="Cancel"
            color="grey-7"
            @click="showLogoutConfirmModal = false"
          />
          <q-btn
            label="Yes, sign out"
            color="negative"
            :loading="isSigningOut"
            :disable="isSigningOut"
            @click="confirmLogout"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-dialog>
</template>

<style scoped lang="scss">
.account-modal :deep(.q-dialog__inner) {
  padding: 0 !important;
  justify-content: flex-end !important;
  align-items: flex-start !important;
}

.account-modal__card {
  position: fixed !important;
  top: 0 !important;
  right: 0 !important;
  margin: 0 !important;
  width: 100%;
  max-width: 420px;
  height: 260px;
  border-radius: 0 !important;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15) !important;
  background: #fff !important;
  display: flex !important;
  flex-direction: column !important;
  z-index: 9999;
}

.account-modal__header {
  display: flex;
  justify-content: flex-start;
}

.account-modal__sign-out {
  border-radius: 0 !important;
  color: var(--q-primary);
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
}

.account-modal__sign-out:hover {
  background: #e60023 !important;
  color: #fff !important;
}

.account-modal__body {
  flex: 1;
  overflow: visible;
}

.account-modal__profile {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.account-modal__avatar-wrap {
  width: 25%;
  padding: 0.25rem 0 0 1rem;
}

.account-modal__avatar {
  width: 80px;
  height: 80px;
  border-radius: 999px;
  object-fit: cover;
  border: 2px solid #fff;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
  background: #f3f4f6;
}

.account-modal__info {
  width: 75%;
  padding-left: 0.5rem;
}

.account-modal__info h6 {
  margin: 0.75rem 0 0.25rem;
  font-size: 1rem;
  font-weight: 700;
  color: #111827;
}

.account-modal__info p {
  margin: 0 0 0.25rem;
  font-size: 0.75rem;
  color: #4b5563;
}

.account-modal__info small {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.7rem;
  color: var(--ls-muted);
}

.account-modal__link {
  padding: 0 !important;
  min-height: 0 !important;
  height: auto !important;
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--q-primary);
}

.account-modal__footer {
  margin-top: auto;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
  justify-content: flex-start;
  gap: 0.25rem;
}

@media (max-width: 768px) {
  .account-modal__card {
    left: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 260px;
  }
}
</style>

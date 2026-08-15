<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { useNavigationStore } from '@/stores/navigation'
import { homePath } from '@/utils/homeRoute'
import logoBw from '@/assets/brand/hub-white.png'
import logoColor from '@/assets/brand/hub-color.png'

const REMEMBER_KEY = 'vizion.remember_login'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()
const dashboard = useDashboardStore()
const navigation = useNavigationStore()

const form = reactive({
  login: '',
  password: '',
  rememberMe: false,
})

const showPassword = ref(false)

const isValidForm = computed(() => {
  return Boolean(form.login.trim() && form.password)
})

function postLoginPath(): string {
  const homePathValue = homePath(auth.user?.permissions)
  const redirect = route.query.redirect
  if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
    if (redirect === '/login' || redirect.startsWith('/login?')) {
      return homePathValue
    }
    return redirect
  }
  return homePathValue
}

function persistRememberMe(loginId: string) {
  if (form.rememberMe) {
    localStorage.setItem(REMEMBER_KEY, loginId)
  } else {
    localStorage.removeItem(REMEMBER_KEY)
  }
}

function onForgotPassword() {
  void router.push({ name: 'reset-password' })
}

function onCreateAccount() {
  $q.dialog({
    title: 'Create an account',
    message: 'Please contact an administrator to create an account.',
    ok: { label: 'Got it', flat: true, color: 'primary' },
  })
}

async function onSubmit() {
  if (!isValidForm.value || auth.loading) return

  const loginId = form.login.trim()
  try {
    await auth.login(loginId, form.password)
    persistRememberMe(loginId)
    $q.notify({ type: 'positive', message: 'Welcome to Vizion', position: 'top' })
    await router.replace(postLoginPath())
    void dashboard.load()
    void navigation.load()
  } catch (err) {
    if (err instanceof Error && err.message === 'mfa_required') {
      await router.push({ name: 'mfa-challenge' })
      return
    }
    $q.notify({
      type: 'negative',
      message: auth.error ?? 'Login failed',
      position: 'top',
    })
  }
}

onMounted(() => {
  const saved = localStorage.getItem(REMEMBER_KEY)
  if (saved) {
    form.login = saved
    form.rememberMe = true
  }
})
</script>

<template>
  <div class="login-container">
    <div class="login-row">
      <div class="brand-panel">
        <div class="brand-content">
          <div class="logo-container">
            <img
              :src="logoBw"
              alt="Vizion"
              class="logo-desktop"
            >
          </div>
        </div>
      </div>

      <div class="form-panel">
        <div class="login-form-container">
          <form
            class="login-form"
            @submit.prevent="onSubmit"
          >
            <div class="mobile-logo-container">
              <img
                :src="logoColor"
                alt="Vizion"
                class="mobile-logo-icon"
              >
            </div>

            <div class="input-container">
              <input
                v-model="form.login"
                type="text"
                class="form-control"
                placeholder=" "
                required
                autocomplete="username"
              >
              <label class="floating-label">Email or username *</label>
            </div>

            <div class="input-container password-container">
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="form-control password-input"
                placeholder=" "
                required
                autocomplete="current-password"
              >
              <label class="floating-label">Password *</label>
              <button
                type="button"
                class="password-toggle-btn"
                :title="showPassword ? 'Hide password' : 'Show password'"
                @click="showPassword = !showPassword"
              >
                <q-icon :name="showPassword ? 'visibility_off' : 'visibility'" />
              </button>
            </div>

            <button
              type="submit"
              :class="['btn', 'login-btn', isValidForm ? 'btn-success' : 'btn-secondary']"
              :disabled="!isValidForm || auth.loading"
            >
              {{ auth.loading ? 'Signing in…' : 'Sign in' }}
            </button>

            <div class="form-options">
              <div class="form-check">
                <input
                  id="rememberMe"
                  v-model="form.rememberMe"
                  type="checkbox"
                  class="form-check-input"
                >
                <label
                  class="form-check-label"
                  for="rememberMe"
                >Remember me</label>
              </div>
              <a
                href="#"
                class="forgot-password"
                @click.prevent="onForgotPassword"
              >Forgot password?</a>
            </div>

            <div class="divider-container">
              <hr class="divider-line">
              <span class="divider-text">or</span>
              <hr class="divider-line">
            </div>

            <button
              type="button"
              class="btn btn-outline-secondary create-account-btn"
              @click="onCreateAccount"
            >
              Create an account
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  height: 100vh;
  overflow: hidden;
  font-family: var(--ls-font-body, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
  background-color: #f8f9fa;
}

.login-row {
  display: flex;
  height: 100vh;
}

.brand-panel {
  background: #0f1419;
  min-height: 100vh;
  flex: 0 0 33.333333%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-content {
  color: white;
  text-align: center;
  animation: fadeInUp 0.8s ease-out;
}

.logo-container {
  margin-bottom: 1rem;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  background: transparent;
}

.logo-desktop {
  width: min(18rem, 70%);
  height: auto;
  max-width: 100%;
  background: transparent;
}

.form-panel {
  background: white;
  min-height: 100vh;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.login-form-container {
  max-width: 360px;
  width: 100%;
  padding: 2rem 0;
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

.mobile-logo-container {
  display: none;
  justify-content: center;
  align-items: center;
  margin-bottom: 1.5rem;
  width: 100%;
  background: transparent;
}

.mobile-logo-icon {
  width: min(100%, 18rem);
  height: auto;
  display: block;
  object-fit: contain;
  background: transparent;
}

.input-container {
  position: relative;
  margin-bottom: 1rem;
}

.password-container {
  position: relative;
}

.password-input {
  padding-right: 3rem;
}

.password-toggle-btn {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  padding: 0.25rem;
  transition: color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  z-index: 5;
}

.password-toggle-btn:hover,
.password-toggle-btn:focus {
  color: #0f1419;
  outline: none;
}

.password-toggle-btn .q-icon {
  font-size: 1.4rem;
}

.form-control {
  border: 1px solid #6b7280;
  border-radius: 12px;
  padding: 0.75rem;
  font-size: 1rem;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
  background-color: white;
  color: #374151;
  width: 100%;
}

.floating-label {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
  font-weight: 400;
  font-size: 1rem;
  transition: all 0.3s ease;
  pointer-events: none;
  background-color: transparent;
  padding: 0;
  z-index: 1;
}

.form-control:focus + .floating-label,
.form-control:not(:placeholder-shown) + .floating-label {
  color: #0f1419;
  font-size: 0.85rem;
  transform: translateY(-2.3rem) translateX(0.15rem);
  background-color: white;
  padding: 0 0.25rem;
  border-radius: 4px;
  z-index: 10;
}

.form-control:focus {
  border-color: #6b7280;
  box-shadow: none;
  outline: none;
}

.btn {
  padding: 0.75rem;
  font-size: 1rem;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  margin-bottom: 1rem;
}

.btn-secondary {
  background-color: #6b7280;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #4b5563;
}

.btn-success {
  background-color: #16a34a;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background-color: #15803d;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 0.75rem;
}

.form-check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.form-check-input {
  width: 1rem;
  height: 1rem;
  margin: 0;
  flex-shrink: 0;
  accent-color: #0f1419;
  cursor: pointer;
}

.form-check-input:focus {
  outline: none;
  box-shadow: none;
}

.form-check-label {
  font-size: 0.9rem;
  color: #6b7280;
  cursor: pointer;
  user-select: none;
}

.forgot-password {
  color: #0f1419;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
}

.forgot-password:hover {
  color: #333333;
  text-decoration: underline;
}

.divider-container {
  display: flex;
  align-items: center;
  margin: 0 0 1.5rem;
}

.divider-line {
  flex: 1;
  height: 1px;
  background-color: #9ca3af;
  border: none;
  margin: 0;
}

.divider-text {
  color: #6b7280;
  font-size: 0.9rem;
  padding: 0 1rem;
  background-color: white;
}

.btn-outline-secondary {
  border: 1px solid #6b7280;
  color: #6b7280;
  background-color: white;
}

.btn-outline-secondary:hover {
  background-color: #0f1419;
  border-color: #0f1419;
  color: white;
}

.create-account-btn {
  border: 1px solid #6b7280;
  color: #6b7280;
  background-color: white;
  border-radius: 8px;
  padding: 0.75rem;
  font-weight: 500;
  font-size: 1rem;
  margin-bottom: 0;
}

.create-account-btn:hover {
  background-color: #0f1419;
  border-color: #0f1419;
  color: white;
  transform: none;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 991.98px) {
  .brand-panel {
    min-height: 40vh;
    flex: 0 0 40%;
  }

  .form-panel {
    min-height: 60vh;
    flex: 1;
  }

  .login-form-container {
    padding: 1.5rem;
  }
}

@media (max-width: 767.98px) {
  .login-row {
    flex-direction: column;
  }

  .brand-panel {
    display: none !important;
  }

  .form-panel {
    width: 100% !important;
    min-height: 100vh;
    background: white;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .login-form-container {
    max-width: 400px;
    width: 100%;
    padding: 2rem 1rem;
    margin: 0 auto;
  }

  .mobile-logo-container {
    display: flex;
  }

  .form-control {
    padding: 0.875rem;
    font-size: 1rem;
  }

  .login-btn {
    padding: 0.875rem;
    font-size: 1rem;
    font-weight: 600;
  }
}

@media (max-width: 575.98px) {
  .login-form-container {
    padding: 1.5rem 0.5rem;
    max-width: 350px;
  }

  .form-control {
    padding: 0.75rem;
  }

  .login-btn {
    padding: 0.75rem;
  }
}
</style>

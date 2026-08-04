<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'

const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()
const dashboard = useDashboardStore()

const form = reactive({
  email: '',
  password: '',
})

async function submit() {
  try {
    await auth.login(form.email, form.password)
    await dashboard.load()
    $q.notify({ type: 'positive', message: 'Bem-vindo ao Lanstar' })
    await router.push({ name: 'dashboard' })
  } catch {
    $q.notify({ type: 'negative', message: auth.error ?? 'Falha no login' })
  }
}
</script>

<template>
  <div class="login">
    <div class="login__atmosphere" aria-hidden="true" />
    <section class="login__panel">
      <p class="login__eyebrow">Acesso corporativo</p>
      <h1>Lanstar</h1>
      <p class="login__lead">
        Entre para ver o painel moldado pelas suas permissões.
      </p>

      <q-form
        class="login__form"
        @submit.prevent="submit"
      >
        <q-input
          v-model="form.email"
          type="email"
          label="E-mail"
          outlined
          dense
          required
          autocomplete="username"
        />
        <q-input
          v-model="form.password"
          type="password"
          label="Senha"
          outlined
          dense
          required
          autocomplete="current-password"
          class="q-mt-md"
        />
        <q-btn
          type="submit"
          class="login__cta q-mt-lg"
          color="primary"
          unelevated
          no-caps
          :loading="auth.loading"
          label="Entrar"
        />
      </q-form>
    </section>
  </div>
</template>

<style scoped lang="scss">
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
  padding: 1.5rem;
}

.login__atmosphere {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 15% 20%, rgba(245, 158, 11, 0.28), transparent 35%),
    radial-gradient(circle at 85% 10%, rgba(15, 118, 110, 0.35), transparent 40%),
    linear-gradient(145deg, #0b1f1c 0%, #115e59 48%, #0f766e 100%);
  animation: drift 14s ease-in-out infinite alternate;
}

.login__panel {
  position: relative;
  z-index: 1;
  width: min(100%, 420px);
  padding: 2.4rem 2rem 2.2rem;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(10px);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.22);
  animation: enter 560ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.login__eyebrow {
  margin: 0;
  color: var(--ls-accent);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.72rem;
  font-weight: 600;
}

.login h1 {
  margin: 0.45rem 0 0.55rem;
  font-family: var(--ls-font-display);
  font-size: clamp(2.4rem, 6vw, 3.2rem);
  line-height: 1;
  color: var(--ls-ink);
}

.login__lead {
  margin: 0 0 1.6rem;
  color: var(--ls-muted);
}

.login__cta {
  width: 100%;
  min-height: 44px;
  font-weight: 600;
}

@keyframes drift {
  from {
    transform: scale(1);
  }
  to {
    transform: scale(1.06);
  }
}

@keyframes enter {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

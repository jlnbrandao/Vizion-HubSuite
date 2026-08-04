<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import WidgetRenderer from '@/components/dashboard/WidgetRenderer.vue'

const auth = useAuthStore()
const dashboard = useDashboardStore()

onMounted(async () => {
  await dashboard.load()
})
</script>

<template>
  <q-page class="dashboard">
    <header class="dashboard__hero">
      <div>
        <p class="dashboard__eyebrow">Painel</p>
        <h1>Olá, {{ auth.user?.fullName }}</h1>
        <p class="dashboard__lead">
          Menu, cards e indicadores compostos pelas suas permissões — sem regras
          espalhadas na interface.
        </p>
      </div>
      <div class="dashboard__roles">
        <span
          v-for="role in auth.user?.roleNames ?? []"
          :key="role"
        >{{ role }}</span>
      </div>
    </header>

    <div
      v-if="dashboard.loading"
      class="dashboard__loading"
    >
      <q-spinner
        color="primary"
        size="40px"
      />
    </div>

    <p
      v-else-if="dashboard.error"
      class="dashboard__error"
    >
      {{ dashboard.error }}
    </p>

    <p
      v-else-if="!dashboard.widgets.length"
      class="dashboard__empty"
    >
      Nenhuma seção de dashboard disponível para o seu perfil.
    </p>

    <div
      v-else
      class="dashboard__grid"
    >
      <WidgetRenderer
        v-for="widget in dashboard.widgets"
        :key="widget.id"
        :widget="widget"
      />
    </div>
  </q-page>
</template>

<style scoped lang="scss">
.dashboard {
  padding: 1.5rem 1.5rem 2.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard__hero {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
  align-items: flex-start;
  margin-bottom: 1.75rem;
  padding: 1.4rem 1.5rem;
  border-radius: 22px;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(245, 158, 11, 0.1)),
    #fff;
  border: 1px solid var(--ls-line);
  animation: fade 500ms ease both;
}

.dashboard__eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.72rem;
  color: var(--ls-accent);
  font-weight: 600;
}

.dashboard__hero h1 {
  margin: 0.35rem 0 0.4rem;
  font-family: var(--ls-font-display);
  font-size: clamp(1.8rem, 3vw, 2.4rem);
}

.dashboard__lead {
  margin: 0;
  max-width: 42rem;
  color: var(--ls-muted);
}

.dashboard__roles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.dashboard__roles span {
  background: var(--ls-ink);
  color: #fff;
  border-radius: 999px;
  padding: 0.3rem 0.7rem;
  font-size: 0.75rem;
  letter-spacing: 0.04em;
}

.dashboard__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.dashboard__loading,
.dashboard__empty,
.dashboard__error {
  display: grid;
  place-items: center;
  min-height: 180px;
  color: var(--ls-muted);
}

@keyframes fade {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 720px) {
  .dashboard__hero {
    flex-direction: column;
  }
}
</style>

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
  <q-page class="app-page">
    <q-card
      class="app-page__card"
      flat
    >
      <q-card-section class="app-page__section">
        <header class="app-page__header">
          <div>
            <h1 class="app-page__title">
              Hello, {{ auth.user?.fullName }}
            </h1>
            <p class="app-page__lead">
              Menu, cards, and indicators composed from your permissions — no
              scattered UI rules.
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
          class="dashboard__state"
        >
          <q-spinner
            color="primary"
            size="40px"
          />
        </div>

        <p
          v-else-if="dashboard.error"
          class="dashboard__state app-page__muted"
        >
          {{ dashboard.error }}
        </p>

        <p
          v-else-if="!dashboard.widgets.length"
          class="dashboard__state app-page__muted"
        >
          No dashboard sections available for your profile.
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
      </q-card-section>
    </q-card>
  </q-page>
</template>

<style scoped lang="scss">
.dashboard__roles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.dashboard__roles span {
  background: #f3f4f6;
  color: #111827;
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

.dashboard__state {
  display: grid;
  place-items: center;
  min-height: 180px;
  margin: 0;
}
</style>

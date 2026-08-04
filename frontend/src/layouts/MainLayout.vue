<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { usePermissions } from '@/composables/usePermissions'

const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()
const dashboard = useDashboardStore()
const { can } = usePermissions()

const menuItems = computed(() =>
  dashboard.menu.filter((item) => can(item.required_permission)),
)

onMounted(async () => {
  if (!dashboard.widgets.length) {
    await dashboard.load()
  }
})

async function logout() {
  await auth.logout()
  dashboard.clear()
  await router.push({ name: 'login' })
  $q.notify({ type: 'positive', message: 'Sessão encerrada' })
}
</script>

<template>
  <q-layout
    view="lHh Lpr lFf"
    class="main-layout"
  >
    <q-header
      elevated
      class="main-layout__header"
    >
      <q-toolbar>
        <q-toolbar-title class="brand">
          Lanstar
        </q-toolbar-title>
        <div class="user-chip">
          <span>{{ auth.user?.fullName }}</span>
          <small>{{ auth.user?.roleNames.join(' · ') || 'sem role' }}</small>
        </div>
        <q-btn
          flat
          dense
          label="Sair"
          @click="logout"
        />
      </q-toolbar>
    </q-header>

    <q-drawer
      show-if-above
      bordered
      :width="260"
      class="main-layout__drawer"
    >
      <div class="drawer-brand">
        <p>Navegação</p>
        <strong>Menu por permissão</strong>
      </div>
      <q-list padding>
        <q-item
          clickable
          v-ripple
          :to="{ name: 'dashboard' }"
          exact
        >
          <q-item-section avatar>
            <q-icon name="dashboard" />
          </q-item-section>
          <q-item-section>Dashboard</q-item-section>
        </q-item>

        <q-item
          v-for="item in menuItems"
          :key="item.id"
          clickable
          v-ripple
          :to="item.route"
        >
          <q-item-section avatar>
            <q-icon :name="item.icon" />
          </q-item-section>
          <q-item-section>{{ item.label }}</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<style scoped lang="scss">
.main-layout__header {
  background: linear-gradient(120deg, #0f766e 0%, #115e59 55%, #0b1f1c 100%);
  color: #fff;
}

.brand {
  font-family: var(--ls-font-display);
  font-size: 1.45rem;
  letter-spacing: 0.02em;
}

.user-chip {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-right: 0.75rem;
  line-height: 1.15;
}

.user-chip small {
  opacity: 0.8;
  font-size: 0.72rem;
}

.main-layout__drawer {
  background: linear-gradient(180deg, #f7fbf9 0%, #eef5f2 100%);
}

.drawer-brand {
  padding: 1.25rem 1.2rem 0.5rem;
}

.drawer-brand p {
  margin: 0;
  color: var(--ls-muted);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.drawer-brand strong {
  font-family: var(--ls-font-display);
  font-size: 1.1rem;
}
</style>

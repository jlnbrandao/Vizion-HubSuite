<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import FakeStuffPage from '@/components/stuff/FakeStuffPage.vue'

const auth = useAuthStore()

const rows = computed(() => [
  {
    id: 'tenant',
    title: auth.user?.tenantName || auth.user?.tenantSlug || '—',
    meta: 'Tenant',
    status: auth.user?.tenantSlug || '—',
  },
  {
    id: 'name',
    title: auth.user?.fullName || '—',
    meta: 'Full name',
    status: 'Account',
  },
  {
    id: 'email',
    title: auth.user?.email || '—',
    meta: 'Email',
    status: 'Login',
  },
  {
    id: 'roles',
    title: auth.user?.roleNames.join(' · ') || '—',
    meta: 'Roles',
    status: 'RBAC',
  },
])
</script>

<template>
  <FakeStuffPage
    title="My account"
    lead="Demo account page opened from the AccountModal."
    :role-badge="auth.user?.roleNames[0] || 'USER'"
    :stats="[
      { label: 'Tenant', value: auth.user?.tenantName || auth.user?.tenantSlug || '—' },
      { label: 'ID', value: (auth.user?.id || '—').slice(0, 8) },
      { label: 'Permissions', value: String(auth.user?.permissions.length ?? 0) },
    ]"
    :rows="rows"
  />
</template>

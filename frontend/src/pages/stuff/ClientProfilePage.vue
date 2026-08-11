<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import FakeStuffPage from '@/components/stuff/FakeStuffPage.vue'

const auth = useAuthStore()

const rows = computed(() => [
  {
    id: 'email',
    title: auth.user?.email || '—',
    meta: 'Account email',
    status: 'Active',
  },
  {
    id: 'roles',
    title: auth.user?.roleNames.join(', ') || 'CLIENT',
    meta: 'Assigned roles',
    status: 'Profile',
  },
  {
    id: 'access',
    title: 'Access limited to own data',
    meta: 'CLIENT policy',
    status: 'Self only',
  },
])
</script>

<template>
  <FakeStuffPage
    title="My data"
    :lead="`Client area for ${auth.user?.fullName || 'user'}. Fake content to present the CLIENT profile.`"
    role-badge="CLIENT"
    :stats="[
      { label: 'Status', value: 'Active' },
      { label: 'Permissions', value: String(auth.user?.permissions.length ?? 0) },
      { label: 'Roles', value: String(auth.user?.roleNames.length ?? 0) },
    ]"
    :rows="rows"
  />
</template>

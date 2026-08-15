<script setup lang="ts">
import FakeStuffPage from '@/components/stuff/FakeStuffPage.vue'
</script>

<template>
  <FakeStuffPage
    title="Platform operations"
    lead="Cross-tenant catalog: create, rename, activate, and suspend tenants."
    role-badge="PLATFORM"
    :stats="[
      { label: 'Scope', value: 'SaaS' },
      { label: 'Focus', value: 'Tenants' },
      { label: 'Host', value: 'ows.*' },
    ]"
    :rows="[
      { id: 'tenants', title: 'Tenants', meta: 'Catalog CRUD + activate/deactivate', status: '/tenants' },
    ]"
    note="Use the Tenants screen for real catalog operations. Tenant ADMINs cannot access this area."
  />
</template>

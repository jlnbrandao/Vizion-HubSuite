<script setup lang="ts">
import FakeStuffPage from '@/components/stuff/FakeStuffPage.vue'
</script>

<template>
  <FakeStuffPage
    title="RBAC Administration"
    lead="ADMIN visual area for identity management: users, roles, and permissions."
    role-badge="ADMIN"
    :stats="[
      { label: 'Modules', value: '3' },
      { label: 'Focus', value: 'RBAC' },
      { label: 'Scope', value: 'Identity' },
    ]"
    :rows="[
      { id: 'users', title: 'Users', meta: 'CRUD + role assignment', status: '/users' },
      { id: 'roles', title: 'Roles', meta: 'CRUD + permissions', status: '/roles' },
      { id: 'perms', title: 'Permissions', meta: 'System catalog', status: '/permissions' },
    ]"
    note="The real Users/Roles/Permissions screens already exist; this page reinforces the ADMIN block in the menu."
  />
</template>

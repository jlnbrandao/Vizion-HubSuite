<script setup lang="ts">
import FakeStuffPage from '@/components/stuff/FakeStuffPage.vue'
</script>

<template>
  <FakeStuffPage
    title="Read-only view"
    lead="Demo overview for the VIEWER profile — view without creating, editing, or deleting."
    role-badge="VIEWER"
    :stats="[
      { label: 'Allowed', value: 'View' },
      { label: 'Denied', value: 'Create' },
      { label: 'Denied', value: 'Edit' },
      { label: 'Denied', value: 'Delete' },
    ]"
    :rows="[
      { id: '1', title: 'Users catalog', meta: 'Read available', status: 'OK' },
      { id: '2', title: 'Roles catalog', meta: 'Read available', status: 'OK' },
      { id: '3', title: 'Permissions catalog', meta: 'Read available', status: 'OK' },
    ]"
    note="Fake page to visually reinforce the VIEWER read-only access."
  />
</template>

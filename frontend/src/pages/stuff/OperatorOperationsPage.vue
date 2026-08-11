<script setup lang="ts">
import FakeStuffPage from '@/components/stuff/FakeStuffPage.vue'
</script>

<template>
  <FakeStuffPage
    title="Today's operations"
    lead="Demo operational queue for the OPERATOR profile to run daily routines."
    role-badge="OPERATOR"
    :stats="[
      { label: 'Pending', value: '14' },
      { label: 'Completed', value: '9' },
      { label: 'Overdue', value: '2' },
    ]"
    :rows="[
      { id: 'op-1', title: 'Check shipment #4412', meta: 'High priority', status: 'Queue' },
      { id: 'op-2', title: 'Update order status #8891', meta: 'SLA 2h', status: 'In progress' },
      { id: 'op-3', title: 'Log incident #120', meta: 'Support', status: 'Queue' },
    ]"
  />
</template>

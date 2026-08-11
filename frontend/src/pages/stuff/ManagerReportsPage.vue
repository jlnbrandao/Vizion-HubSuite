<script setup lang="ts">
import FakeStuffPage from '@/components/stuff/FakeStuffPage.vue'
</script>

<template>
  <FakeStuffPage
    title="Reports"
    lead="Visual catalog of management reports. The data below is static for presentation."
    role-badge="MANAGER"
    :stats="[
      { label: 'Active reports', value: '12' },
      { label: 'Scheduled', value: '5' },
      { label: 'Exports', value: '38' },
    ]"
    :rows="[
      { id: 'sales-weekly', title: 'Weekly sales', meta: 'CSV · PDF', status: 'Ready' },
      { id: 'pipeline', title: 'Sales pipeline', meta: 'Read only', status: 'Ready' },
      { id: 'headcount', title: 'Headcount', meta: 'Consolidated HR', status: 'Draft' },
    ]"
  />
</template>

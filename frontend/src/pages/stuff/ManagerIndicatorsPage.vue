<script setup lang="ts">
import FakeStuffPage from '@/components/stuff/FakeStuffPage.vue'
</script>

<template>
  <FakeStuffPage
    title="Company indicators"
    lead="Demo panel of commercial and operational KPIs for the MANAGER profile."
    role-badge="MANAGER"
    :stats="[
      { label: 'MTD revenue', value: '$128,450' },
      { label: 'MTD orders', value: '842' },
      { label: 'Conversion', value: '3.7%' },
      { label: 'NPS', value: '72' },
    ]"
    :rows="[
      { id: '1', title: 'Sales pipeline', meta: 'Updated 2h ago', status: 'Rising' },
      { id: '2', title: 'Average ticket', meta: 'Weekly comparison', status: '+4.2%' },
      { id: '3', title: 'Projected churn', meta: 'Last 30 days', status: 'Stable' },
    ]"
  />
</template>

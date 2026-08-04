<script setup lang="ts">
defineProps<{ data: Record<string, unknown> }>()
</script>

<template>
  <dl class="profile">
    <div>
      <dt>Nome</dt>
      <dd>{{ data.full_name }}</dd>
    </div>
    <div>
      <dt>E-mail</dt>
      <dd>{{ data.email }}</dd>
    </div>
    <div>
      <dt>Status</dt>
      <dd>{{ data.is_active ? 'Ativo' : 'Inativo' }}</dd>
    </div>
  </dl>
</template>

<style scoped lang="scss">
.profile {
  margin: 0;
  display: grid;
  gap: 0.85rem;
}

.profile dt {
  color: var(--ls-muted);
  font-size: 0.78rem;
}

.profile dd {
  margin: 0.15rem 0 0;
  font-weight: 600;
}
</style>

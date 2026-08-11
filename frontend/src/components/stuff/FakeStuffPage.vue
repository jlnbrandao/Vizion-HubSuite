<script setup lang="ts">
export interface FakeStat {
  label: string
  value: string
}

export interface FakeRow {
  id: string
  title: string
  meta: string
  status: string
}

withDefaults(
  defineProps<{
    title: string
    lead: string
    roleBadge: string
    stats?: FakeStat[]
    rows?: FakeRow[]
    note?: string
  }>(),
  {
    stats: () => [],
    rows: () => [],
    note: 'Demo content for visual presentation of the profile.',
  },
)
</script>

<template>
  <q-page class="app-page">
    <q-card
      class="app-page__card"
      flat
    >
      <q-card-section class="app-page__section">
        <header class="app-page__header">
          <div>
            <h1 class="app-page__title">{{ title }}</h1>
            <p class="app-page__lead">{{ lead }}</p>
          </div>
          <span class="fake-page__badge">{{ roleBadge }}</span>
        </header>

        <section
          v-if="stats.length"
          class="fake-page__stats"
        >
          <article
            v-for="stat in stats"
            :key="stat.label"
            class="fake-page__stat"
          >
            <small>{{ stat.label }}</small>
            <strong>{{ stat.value }}</strong>
          </article>
        </section>

        <section
          v-if="rows.length"
          class="fake-page__panel"
        >
          <h2>Demo items</h2>
          <ul>
            <li
              v-for="row in rows"
              :key="row.id"
            >
              <div>
                <strong>{{ row.title }}</strong>
                <span>{{ row.meta }}</span>
              </div>
              <em>{{ row.status }}</em>
            </li>
          </ul>
        </section>

        <p class="app-page__muted fake-page__note">{{ note }}</p>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<style scoped lang="scss">
.fake-page__badge {
  flex-shrink: 0;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: #f3f4f6;
  color: #111827;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.fake-page__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}

.fake-page__stat {
  padding: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  background: var(--app-content-background, #ffffff);
}

.fake-page__stat small {
  display: block;
  color: #9ca3af;
  font-size: 0.75rem;
  margin-bottom: 0.35rem;
}

.fake-page__stat strong {
  font-size: 1.35rem;
  font-weight: 700;
  color: #111827;
}

.fake-page__panel {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  background: var(--app-content-background, #ffffff);
  padding: 1rem 1.1rem 0.35rem;
  margin-bottom: 1rem;
}

.fake-page__panel h2 {
  margin: 0 0 0.75rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
}

.fake-page__panel ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.fake-page__panel li {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 0.85rem 0;
  border-top: 1px solid #e5e7eb;
}

.fake-page__panel li strong {
  display: block;
  font-size: 0.95rem;
  color: #111827;
}

.fake-page__panel li span {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.8rem;
  color: #9ca3af;
}

.fake-page__panel em {
  font-style: normal;
  font-size: 0.75rem;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
}

.fake-page__note {
  margin: 0;
  font-size: 0.82rem;
}
</style>

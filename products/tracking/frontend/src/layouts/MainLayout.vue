<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

async function logout() {
  await auth.logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <q-layout view="hHh lpR fFf">
    <q-header class="bg-teal-8">
      <q-toolbar>
        <q-toolbar-title>OpenVizion Tracking</q-toolbar-title>
        <q-btn flat to="/" label="Map" />
        <q-btn flat to="/devices" label="Devices" />
        <q-btn flat to="/geofences" label="Geofences" />
        <q-space />
        <div class="q-mr-md">{{ auth.user?.email }}</div>
        <q-btn flat label="Sign out" @click="logout" />
      </q-toolbar>
    </q-header>
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export function createTrackingRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/login',
        name: 'login',
        component: () => import('@/pages/LoginPage.vue'),
        meta: { public: true },
      },
      {
        path: '/',
        component: () => import('@/layouts/MainLayout.vue'),
        children: [
          { path: '', name: 'map', component: () => import('@/pages/MapPage.vue') },
          { path: 'devices', name: 'devices', component: () => import('@/pages/DevicesPage.vue') },
          { path: 'geofences', name: 'geofences', component: () => import('@/pages/GeofencesPage.vue') },
        ],
      },
    ],
  })

  router.beforeEach((to) => {
    const auth = useAuthStore()
    if (to.meta.public) {
      return true
    }
    if (!auth.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    return true
  })

  return router
}

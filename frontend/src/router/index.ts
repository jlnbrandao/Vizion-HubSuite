import {
  createRouter,
  createWebHistory,
  type RouteLocationRaw,
  type RouteRecordRaw,
} from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { PermissionCode } from '@/constants/permissions'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    requiresAuth?: boolean
    permissions?: string[]
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: { name: 'dashboard' },
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/pages/DashboardPage.vue'),
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('@/pages/UsersPage.vue'),
        meta: { permissions: [PermissionCode.USERS_READ] },
      },
      {
        path: 'roles',
        name: 'roles',
        component: () => import('@/pages/RolesPage.vue'),
        meta: { permissions: [PermissionCode.ROLES_READ] },
      },
      {
        path: 'permissions',
        name: 'permissions',
        component: () => import('@/pages/PermissionsPage.vue'),
        meta: { permissions: [PermissionCode.PERMISSIONS_READ] },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    redirect: () => ({ name: 'dashboard' }),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function resolvePostLoginTarget(redirect: unknown): RouteLocationRaw {
  if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
    if (redirect === '/login' || redirect.startsWith('/login?')) {
      return { name: 'dashboard' }
    }
    return redirect
  }
  return { name: 'dashboard' }
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!auth.bootstrapped) {
    await auth.bootstrap()
  }

  const isPublic = Boolean(to.meta.public) || to.name === 'login'

  if (isPublic) {
    if (auth.isAuthenticated) {
      return resolvePostLoginTarget(to.query.redirect)
    }
    return true
  }

  const needsAuth = to.matched.some((record) => record.meta.requiresAuth === true)
  if (needsAuth && !auth.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  const required = to.meta.permissions ?? []
  if (required.length) {
    const granted = new Set(auth.user?.permissions ?? [])
    const allowed = required.every((code) => granted.has(code))
    if (!allowed) {
      return { name: 'dashboard' }
    }
  }

  return true
})

export default router

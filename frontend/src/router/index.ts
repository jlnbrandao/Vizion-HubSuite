import {
  createRouter,
  createWebHistory,
  type RouteLocationRaw,
  type RouteRecordRaw,
} from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { hasPermissionCode, PermissionCode } from '@/constants/permissions'
import { billingRoutes } from '@/modules/billing/routes'
import { iamPublicRoutes, iamRoutes } from '@/modules/iam/routes'
import { integrationRoutes } from '@/modules/integration/routes'
import { platformRoutes } from '@/modules/platform/routes'
import { resolveHomeRoute, resolveHomeRouteName } from '@/utils/homeRoute'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    requiresAuth?: boolean
    /** Service that owns the route; must be entitled for the tenant. */
    service?: string
    /** All of these codes are required. */
    permissions?: string[]
    /** At least one of these codes is required. */
    anyPermissions?: string[]
  }
}

/** Cross-service shell routes: dashboards and per-profile landing pages. */
const shellRoutes: RouteRecordRaw[] = [
  {
    path: '',
    redirect: () => {
      const auth = useAuthStore()
      return resolveHomeRoute(auth.user?.permissions)
    },
  },
  {
    path: 'dashboard',
    name: 'dashboard',
    component: () => import('@/pages/DashboardPage.vue'),
  },
  {
    path: 'admin',
    name: 'admin-overview',
    component: () => import('@/pages/stuff/AdminOverviewPage.vue'),
    meta: { permissions: [PermissionCode.DASHBOARD_ADMIN] },
  },
  {
    path: 'reports/indicators',
    name: 'manager-indicators',
    component: () => import('@/pages/stuff/ManagerIndicatorsPage.vue'),
    meta: { permissions: [PermissionCode.DASHBOARD_MANAGER] },
  },
  {
    path: 'reports',
    name: 'manager-reports',
    component: () => import('@/pages/stuff/ManagerReportsPage.vue'),
    meta: { permissions: [PermissionCode.DASHBOARD_MANAGER] },
  },
  {
    path: 'operations/today',
    name: 'operator-operations',
    component: () => import('@/pages/stuff/OperatorOperationsPage.vue'),
    meta: { permissions: [PermissionCode.DASHBOARD_OPERATOR] },
  },
  {
    path: 'me',
    name: 'client-profile',
    component: () => import('@/pages/stuff/ClientProfilePage.vue'),
    meta: { permissions: [PermissionCode.DASHBOARD_CLIENT] },
  },
  {
    path: 'dashboard/readonly',
    name: 'viewer-readonly',
    component: () => import('@/pages/stuff/ViewerReadonlyPage.vue'),
    meta: { permissions: [PermissionCode.DASHBOARD_VIEWER] },
  },
  {
    path: 'account/profile',
    name: 'account-profile',
    component: () => import('@/pages/stuff/AccountProfilePage.vue'),
  },
]

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { public: true },
  },
  {
    // Client opening page — full-viewport map (same shell as temp MainPage), no MainLayout chrome
    path: '/main',
    name: 'main',
    component: () => import('@/pages/MainPage.vue'),
    meta: {
      requiresAuth: true,
      permissions: [PermissionCode.DASHBOARD_CLIENT],
    },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      ...shellRoutes,
      ...iamRoutes,
      ...platformRoutes,
      ...integrationRoutes,
      ...billingRoutes,
    ],
  },
  ...iamPublicRoutes,
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    redirect: () => {
      const auth = useAuthStore()
      return resolveHomeRoute(auth.user?.permissions)
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function resolvePostLoginTarget(
  redirect: unknown,
  permissions: readonly string[] | undefined,
): RouteLocationRaw {
  if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
    if (redirect === '/login' || redirect.startsWith('/login?')) {
      return resolveHomeRoute(permissions)
    }
    return redirect
  }
  return resolveHomeRoute(permissions)
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!auth.bootstrapped) {
    await auth.bootstrap()
  }

  const isPublic =
    Boolean(to.meta.public) ||
    to.name === 'login' ||
    to.name === 'reset-password' ||
    to.name === 'mfa-challenge'

  if (isPublic) {
    if (auth.isAuthenticated) {
      return resolvePostLoginTarget(to.query.redirect, auth.user?.permissions)
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

  // Service entitlement first: an unlicensed service is never reachable, even
  // when the user happens to hold its permissions.
  const service = to.meta.service
  if (service && !auth.isEntitled(service)) {
    return resolveHomeRoute(auth.user?.permissions)
  }

  const required = to.meta.permissions ?? []
  const anyRequired = to.meta.anyPermissions ?? []
  if (required.length || anyRequired.length) {
    const granted = new Set(auth.user?.permissions ?? [])
    const allowed =
      required.every((code) => hasPermissionCode(granted, code)) &&
      (anyRequired.length === 0 ||
        anyRequired.some((code) => hasPermissionCode(granted, code)))
    if (!allowed) {
      return resolveHomeRoute(auth.user?.permissions)
    }
  }

  // Client home is the map — bounce composed dashboard away for CLIENT-only users
  if (to.name === 'dashboard' && resolveHomeRouteName(auth.user?.permissions) === 'main') {
    return { name: 'main' }
  }

  return true
})

export default router

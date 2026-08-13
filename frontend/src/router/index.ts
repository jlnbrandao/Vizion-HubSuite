import {
  createRouter,
  createWebHistory,
  type RouteLocationRaw,
  type RouteRecordRaw,
} from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { PermissionCode } from '@/constants/permissions'
import { resolveHomeRoute, resolveHomeRouteName } from '@/utils/homeRoute'

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
      {
        path: 'platform',
        name: 'platform-overview',
        component: () => import('@/pages/stuff/PlatformOverviewPage.vue'),
        meta: { permissions: [PermissionCode.DASHBOARD_PLATFORM] },
      },
      {
        path: 'tenants',
        name: 'tenants',
        component: () => import('@/pages/TenantsPage.vue'),
        meta: { permissions: [PermissionCode.TENANTS_READ] },
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
      {
        path: 'iam/audit',
        name: 'iam-audit',
        component: () => import('@/pages/iam/AuditPage.vue'),
        meta: { permissions: [PermissionCode.AUDIT_READ] },
      },
      {
        path: 'iam/mfa',
        name: 'iam-mfa',
        component: () => import('@/pages/iam/MfaSetupPage.vue'),
      },
      {
        path: 'iam/oauth-clients',
        name: 'iam-oauth-clients',
        component: () => import('@/pages/iam/OAuthClientsPage.vue'),
        meta: { permissions: [PermissionCode.OAUTH_CLIENTS_READ] },
      },
      {
        path: 'iam/federation',
        name: 'iam-federation',
        component: () => import('@/pages/iam/FederationPage.vue'),
        meta: { permissions: [PermissionCode.FEDERATION_READ] },
      },
      {
        path: 'iam/api-keys',
        name: 'iam-api-keys',
        component: () => import('@/pages/iam/MachineIdentitiesPage.vue'),
        meta: { permissions: [PermissionCode.API_KEYS_READ] },
      },
      {
        path: 'integrations',
        name: 'integrations',
        component: () => import('@/pages/IntegrationPage.vue'),
        meta: { permissions: [PermissionCode.INTEGRATION_READ] },
      },
    ],
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('@/pages/iam/ResetPasswordPage.vue'),
    meta: { public: true },
  },
  {
    path: '/mfa',
    name: 'mfa-challenge',
    component: () => import('@/pages/iam/MfaChallengePage.vue'),
    meta: { public: true },
  },
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

  const required = to.meta.permissions ?? []
  if (required.length) {
    const granted = new Set(auth.user?.permissions ?? [])
    const allowed = required.every((code) => granted.has(code))
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

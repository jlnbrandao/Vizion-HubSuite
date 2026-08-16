import type { RouteRecordRaw } from 'vue-router'
import { PermissionCode, PermissionService } from '@/constants/permissions'

export const platformRoutes: RouteRecordRaw[] = [
  {
    path: 'tenants',
    name: 'tenants',
    component: () => import('@/modules/platform/pages/TenantsPage.vue'),
    meta: {
      service: PermissionService.PLATFORM,
      permissions: [PermissionCode.TENANTS_READ],
    },
  },
  {
    path: 'platform/services',
    name: 'platform-services',
    component: () => import('@/modules/platform/pages/EntitlementsPage.vue'),
    meta: {
      service: PermissionService.PLATFORM,
      permissions: [PermissionCode.SERVICES_READ],
    },
  },
  {
    path: 'platform/products',
    name: 'platform-products',
    component: () => import('@/modules/platform/pages/ProductsPage.vue'),
    meta: {
      service: PermissionService.PLATFORM,
      permissions: [PermissionCode.PRODUCTS_READ],
    },
  },
  {
    path: 'usage',
    name: 'usage',
    component: () => import('@/modules/platform/pages/UsagePage.vue'),
    meta: {
      service: PermissionService.PLATFORM,
      // Tenant admins read their own usage; the platform reads any tenant's.
      anyPermissions: [PermissionCode.USAGE_READ, PermissionCode.USAGE_READ_ALL],
    },
  },
]

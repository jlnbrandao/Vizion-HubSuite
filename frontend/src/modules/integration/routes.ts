import type { RouteRecordRaw } from 'vue-router'
import { PermissionCode, PermissionService } from '@/constants/permissions'

export const integrationRoutes: RouteRecordRaw[] = [
  {
    path: 'integrations',
    name: 'integrations',
    component: () => import('@/modules/integration/pages/IntegrationPage.vue'),
    meta: {
      service: PermissionService.INTEGRATION,
      permissions: [PermissionCode.INTEGRATION_READ],
    },
  },
]

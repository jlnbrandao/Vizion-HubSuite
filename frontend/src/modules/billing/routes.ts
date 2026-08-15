import type { RouteRecordRaw } from 'vue-router'
import { PermissionCode, PermissionService } from '@/constants/permissions'

export const billingRoutes: RouteRecordRaw[] = [
  {
    path: 'account/billing',
    name: 'account-billing',
    component: () => import('@/modules/billing/pages/BillingPage.vue'),
    meta: {
      service: PermissionService.BILLING,
      permissions: [PermissionCode.INVOICES_READ],
    },
  },
]

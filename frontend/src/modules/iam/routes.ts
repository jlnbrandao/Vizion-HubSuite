import type { RouteRecordRaw } from 'vue-router'
import { PermissionCode, PermissionService } from '@/constants/permissions'

/** Routes rendered inside MainLayout. Public IAM routes live in `publicRoutes`. */
export const iamRoutes: RouteRecordRaw[] = [
  {
    path: 'users',
    name: 'users',
    component: () => import('@/modules/iam/pages/UsersPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.USERS_READ] },
  },
  {
    path: 'roles',
    name: 'roles',
    component: () => import('@/modules/iam/pages/RolesPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.ROLES_READ] },
  },
  {
    path: 'permissions',
    name: 'permissions',
    component: () => import('@/modules/iam/pages/PermissionsPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.PERMISSIONS_READ] },
  },
  {
    path: 'iam/audit',
    name: 'iam-audit',
    component: () => import('@/modules/iam/pages/AuditPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.AUDIT_READ] },
  },
  {
    path: 'iam/sessions',
    name: 'iam-sessions',
    component: () => import('@/modules/iam/pages/SessionsPage.vue'),
    meta: { service: PermissionService.IAM },
  },
  {
    path: 'iam/policies',
    name: 'iam-policies',
    component: () => import('@/modules/iam/pages/PoliciesPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.POLICIES_READ] },
  },
  {
    path: 'iam/mfa',
    name: 'iam-mfa',
    component: () => import('@/modules/iam/pages/MfaSetupPage.vue'),
    meta: { service: PermissionService.IAM },
  },
  {
    path: 'iam/oauth-clients',
    name: 'iam-oauth-clients',
    component: () => import('@/modules/iam/pages/OAuthClientsPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.OAUTH_CLIENTS_READ] },
  },
  {
    path: 'iam/federation',
    name: 'iam-federation',
    component: () => import('@/modules/iam/pages/FederationPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.FEDERATION_READ] },
  },
  {
    path: 'iam/api-keys',
    name: 'iam-api-keys',
    component: () => import('@/modules/iam/pages/MachineIdentitiesPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.API_KEYS_READ] },
  },
  {
    path: 'iam/acls',
    name: 'iam-acls',
    component: () => import('@/modules/iam/pages/AclPage.vue'),
    meta: { service: PermissionService.IAM, permissions: [PermissionCode.ACL_READ] },
  },
]

export const iamPublicRoutes: RouteRecordRaw[] = [
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('@/modules/iam/pages/ResetPasswordPage.vue'),
    meta: { public: true },
  },
  {
    path: '/mfa',
    name: 'mfa-challenge',
    component: () => import('@/modules/iam/pages/MfaChallengePage.vue'),
    meta: { public: true },
  },
]

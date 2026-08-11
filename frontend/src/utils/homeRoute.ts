import type { RouteLocationRaw } from 'vue-router'
import { PermissionCode } from '@/constants/permissions'

const COMPOSED_DASHBOARD_PERMISSIONS = [
  PermissionCode.DASHBOARD_ADMIN,
  PermissionCode.DASHBOARD_MANAGER,
  PermissionCode.DASHBOARD_OPERATOR,
  PermissionCode.DASHBOARD_VIEWER,
] as const

export type HomeRouteName = 'main' | 'dashboard'

/** Opening page: CLIENT map (/main) vs composed dashboard. */
export function resolveHomeRouteName(
  permissions: readonly string[] | undefined,
): HomeRouteName {
  const granted = new Set(permissions ?? [])
  const isClientMap =
    granted.has(PermissionCode.DASHBOARD_CLIENT) &&
    !COMPOSED_DASHBOARD_PERMISSIONS.some((code) => granted.has(code))

  return isClientMap ? 'main' : 'dashboard'
}

export function resolveHomeRoute(permissions: readonly string[] | undefined): RouteLocationRaw {
  return { name: resolveHomeRouteName(permissions) }
}

export function isClientMapHome(permissions: readonly string[] | undefined): boolean {
  return resolveHomeRouteName(permissions) === 'main'
}

export function homePath(permissions: readonly string[] | undefined): string {
  return resolveHomeRouteName(permissions) === 'main' ? '/main' : '/dashboard'
}

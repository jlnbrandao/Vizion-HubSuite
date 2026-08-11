/** Canonical permission codes — mirror backend PermissionCode. */

/** Standardized action verbs — prefer bare verbs scoped by resource. */
export const PermissionAction = {
  CREATE: 'create',
  READ: 'read',
  UPDATE: 'update',
  DELETE: 'delete',
  LIST: 'list',
  MANAGE: 'manage',
  EXPORT: 'export',
  IMPORT: 'import',
  APPROVE: 'approve',
  CANCEL: 'cancel',
  EXECUTE: 'execute',
  ASSIGN: 'assign',
  LINK: 'link',
  UNLINK: 'unlink',
  ACTIVATE: 'activate',
  DEACTIVATE: 'deactivate',
} as const

export type PermissionActionValue =
  (typeof PermissionAction)[keyof typeof PermissionAction]

export const PermissionCode = {
  USERS_CREATE: 'users.create',
  USERS_READ: 'users.read',
  USERS_UPDATE: 'users.update',
  USERS_DELETE: 'users.delete',
  USERS_ASSIGN: 'users.assign',

  ROLES_CREATE: 'roles.create',
  ROLES_READ: 'roles.read',
  ROLES_UPDATE: 'roles.update',
  ROLES_DELETE: 'roles.delete',
  ROLES_ASSIGN: 'roles.assign',

  PERMISSIONS_CREATE: 'permissions.create',
  PERMISSIONS_READ: 'permissions.read',
  PERMISSIONS_UPDATE: 'permissions.update',
  PERMISSIONS_DELETE: 'permissions.delete',

  DASHBOARD_ADMIN: 'dashboard.admin',
  DASHBOARD_MANAGER: 'dashboard.manager',
  DASHBOARD_OPERATOR: 'dashboard.operator',
  DASHBOARD_CLIENT: 'dashboard.client',
  DASHBOARD_VIEWER: 'dashboard.viewer',

  SYSTEM_SETTINGS: 'system.settings',
} as const

export type PermissionCodeValue = (typeof PermissionCode)[keyof typeof PermissionCode]

export function permissionResource(code: string): string {
  const dot = code.indexOf('.')
  return dot === -1 ? code : code.slice(0, dot)
}

export function permissionAction(code: string): string {
  const dot = code.indexOf('.')
  return dot === -1 ? '' : code.slice(dot + 1)
}

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
  DASHBOARD_PLATFORM: 'dashboard.platform',

  SYSTEM_SETTINGS: 'system.settings',

  TENANTS_CREATE: 'tenants.create',
  TENANTS_READ: 'tenants.read',
  TENANTS_UPDATE: 'tenants.update',
  TENANTS_ACTIVATE: 'tenants.activate',
  TENANTS_DEACTIVATE: 'tenants.deactivate',

  AUDIT_READ: 'audit.read',
  SESSIONS_REVOKE: 'sessions.revoke',
  OAUTH_CLIENTS_CREATE: 'oauth_clients.create',
  OAUTH_CLIENTS_READ: 'oauth_clients.read',
  OAUTH_CLIENTS_UPDATE: 'oauth_clients.update',
  OAUTH_CLIENTS_DELETE: 'oauth_clients.delete',
  SERVICE_ACCOUNTS_CREATE: 'service_accounts.create',
  SERVICE_ACCOUNTS_READ: 'service_accounts.read',
  SERVICE_ACCOUNTS_UPDATE: 'service_accounts.update',
  SERVICE_ACCOUNTS_DELETE: 'service_accounts.delete',
  API_KEYS_CREATE: 'api_keys.create',
  API_KEYS_READ: 'api_keys.read',
  API_KEYS_DELETE: 'api_keys.delete',
  FEDERATION_CREATE: 'federation.create',
  FEDERATION_READ: 'federation.read',
  FEDERATION_UPDATE: 'federation.update',
  FEDERATION_DELETE: 'federation.delete',
  POLICIES_CREATE: 'policies.create',
  POLICIES_READ: 'policies.read',
  POLICIES_UPDATE: 'policies.update',
  POLICIES_DELETE: 'policies.delete',
  SCIM_PROVISION: 'scim.provision',
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

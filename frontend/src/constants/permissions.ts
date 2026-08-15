/**
 * GENERATED FILE — do not edit.
 *
 * Source of truth: backend/src/shared/infrastructure/security/permission_codes.py
 * Regenerate with: cd backend && python -m scripts.generate_frontend_permissions
 *
 * Codes are namespaced as `service.resource.action`. Each entry also carries the
 * legacy `resource.action` alias, which still authorizes during the migration.
 */

export const PermissionAction = {
  ACTIVATE: 'activate',
  APPROVE: 'approve',
  ASSIGN: 'assign',
  CANCEL: 'cancel',
  CREATE: 'create',
  DEACTIVATE: 'deactivate',
  DELETE: 'delete',
  EXECUTE: 'execute',
  EXPORT: 'export',
  IMPORT: 'import',
  LINK: 'link',
  LIST: 'list',
  MANAGE: 'manage',
  READ: 'read',
  UNLINK: 'unlink',
  UPDATE: 'update',
} as const

export type PermissionActionValue =
  (typeof PermissionAction)[keyof typeof PermissionAction]

export const PermissionService = {
  IAM: 'iam',
  INTEGRATION: 'integration',
  PLATFORM: 'platform',
} as const

export type PermissionServiceValue =
  (typeof PermissionService)[keyof typeof PermissionService]

export const PermissionCode = {
  USERS_CREATE: 'iam.users.create',
  USERS_READ: 'iam.users.read',
  USERS_UPDATE: 'iam.users.update',
  USERS_DELETE: 'iam.users.delete',
  USERS_ASSIGN: 'iam.users.assign',
  ROLES_CREATE: 'iam.roles.create',
  ROLES_READ: 'iam.roles.read',
  ROLES_UPDATE: 'iam.roles.update',
  ROLES_DELETE: 'iam.roles.delete',
  ROLES_ASSIGN: 'iam.roles.assign',
  PERMISSIONS_CREATE: 'iam.permissions.create',
  PERMISSIONS_READ: 'iam.permissions.read',
  PERMISSIONS_UPDATE: 'iam.permissions.update',
  PERMISSIONS_DELETE: 'iam.permissions.delete',
  PERMISSION_GROUPS_READ: 'iam.permission_groups.read',
  PERMISSION_GROUPS_MANAGE: 'iam.permission_groups.manage',
  DASHBOARD_ADMIN: 'iam.dashboard.admin',
  DASHBOARD_MANAGER: 'iam.dashboard.manager',
  DASHBOARD_OPERATOR: 'iam.dashboard.operator',
  DASHBOARD_CLIENT: 'iam.dashboard.client',
  DASHBOARD_VIEWER: 'iam.dashboard.viewer',
  DASHBOARD_PLATFORM: 'iam.dashboard.platform',
  SYSTEM_SETTINGS: 'iam.system.settings',
  TENANTS_CREATE: 'platform.tenants.create',
  TENANTS_READ: 'platform.tenants.read',
  TENANTS_UPDATE: 'platform.tenants.update',
  TENANTS_ACTIVATE: 'platform.tenants.activate',
  TENANTS_DEACTIVATE: 'platform.tenants.deactivate',
  SERVICES_READ: 'platform.services.read',
  SERVICES_MANAGE: 'platform.services.manage',
  USAGE_READ: 'platform.usage.read',
  USAGE_READ_ALL: 'platform.usage.read_all',
  AUDIT_READ: 'iam.audit.read',
  SESSIONS_REVOKE: 'iam.sessions.revoke',
  OAUTH_CLIENTS_CREATE: 'iam.oauth_clients.create',
  OAUTH_CLIENTS_READ: 'iam.oauth_clients.read',
  OAUTH_CLIENTS_UPDATE: 'iam.oauth_clients.update',
  OAUTH_CLIENTS_DELETE: 'iam.oauth_clients.delete',
  SERVICE_ACCOUNTS_CREATE: 'iam.service_accounts.create',
  SERVICE_ACCOUNTS_READ: 'iam.service_accounts.read',
  SERVICE_ACCOUNTS_UPDATE: 'iam.service_accounts.update',
  SERVICE_ACCOUNTS_DELETE: 'iam.service_accounts.delete',
  API_KEYS_CREATE: 'iam.api_keys.create',
  API_KEYS_READ: 'iam.api_keys.read',
  API_KEYS_DELETE: 'iam.api_keys.delete',
  FEDERATION_CREATE: 'iam.federation.create',
  FEDERATION_READ: 'iam.federation.read',
  FEDERATION_UPDATE: 'iam.federation.update',
  FEDERATION_DELETE: 'iam.federation.delete',
  POLICIES_CREATE: 'iam.policies.create',
  POLICIES_READ: 'iam.policies.read',
  POLICIES_UPDATE: 'iam.policies.update',
  POLICIES_DELETE: 'iam.policies.delete',
  SCIM_PROVISION: 'iam.scim.provision',
  ACL_READ: 'iam.acl.read',
  ACL_GRANT: 'iam.acl.grant',
  ACL_REVOKE: 'iam.acl.revoke',
  INTEGRATION_READ: 'integration.integration.read',
  INTEGRATION_CREATE: 'integration.integration.create',
  INTEGRATION_UPDATE: 'integration.integration.update',
  INTEGRATION_DELETE: 'integration.integration.delete',
  INTEGRATION_TEST: 'integration.integration.test',
  INTEGRATION_SYNC: 'integration.integration.sync',
  INTEGRATION_LOGS_READ: 'integration.integration.read_logs',
} as const

/** Pre-namespace aliases, accepted by the backend until they are dropped. */
export const PermissionLegacyCode = {
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
  PERMISSION_GROUPS_READ: 'permission_groups.read',
  PERMISSION_GROUPS_MANAGE: 'permission_groups.manage',
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
  SERVICES_READ: 'services.read',
  SERVICES_MANAGE: 'services.manage',
  USAGE_READ: 'usage.read',
  USAGE_READ_ALL: 'usage.read_all',
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
  ACL_READ: 'acl.read',
  ACL_GRANT: 'acl.grant',
  ACL_REVOKE: 'acl.revoke',
  INTEGRATION_READ: 'integration.read',
  INTEGRATION_CREATE: 'integration.create',
  INTEGRATION_UPDATE: 'integration.update',
  INTEGRATION_DELETE: 'integration.delete',
  INTEGRATION_TEST: 'integration.test',
  INTEGRATION_SYNC: 'integration.sync',
  INTEGRATION_LOGS_READ: 'integration.read_logs',
} as const

export type PermissionCodeValue = (typeof PermissionCode)[keyof typeof PermissionCode]

export interface PermissionCatalogEntry {
  code: string
  legacyCode: string
  service: string
  resource: string
  action: string
  name: string
  description: string
}

export const PERMISSION_CATALOG: readonly PermissionCatalogEntry[] = [
  { code: 'iam.users.create', legacyCode: 'users.create', service: 'iam', resource: 'users', action: 'create', name: 'Create users', description: 'Allows creating users' },
  { code: 'iam.users.read', legacyCode: 'users.read', service: 'iam', resource: 'users', action: 'read', name: 'Read users', description: 'Allows viewing users' },
  { code: 'iam.users.update', legacyCode: 'users.update', service: 'iam', resource: 'users', action: 'update', name: 'Update users', description: 'Allows editing users' },
  { code: 'iam.users.delete', legacyCode: 'users.delete', service: 'iam', resource: 'users', action: 'delete', name: 'Delete users', description: 'Allows deleting users' },
  { code: 'iam.users.assign', legacyCode: 'users.assign', service: 'iam', resource: 'users', action: 'assign', name: 'Assign user roles', description: 'Allows assigning and removing user roles' },
  { code: 'iam.roles.create', legacyCode: 'roles.create', service: 'iam', resource: 'roles', action: 'create', name: 'Create roles', description: 'Allows creating roles' },
  { code: 'iam.roles.read', legacyCode: 'roles.read', service: 'iam', resource: 'roles', action: 'read', name: 'Read roles', description: 'Allows viewing roles' },
  { code: 'iam.roles.update', legacyCode: 'roles.update', service: 'iam', resource: 'roles', action: 'update', name: 'Update roles', description: 'Allows editing roles' },
  { code: 'iam.roles.delete', legacyCode: 'roles.delete', service: 'iam', resource: 'roles', action: 'delete', name: 'Delete roles', description: 'Allows deleting roles' },
  { code: 'iam.roles.assign', legacyCode: 'roles.assign', service: 'iam', resource: 'roles', action: 'assign', name: 'Assign role permissions', description: 'Allows assigning and removing role permissions' },
  { code: 'iam.permissions.create', legacyCode: 'permissions.create', service: 'iam', resource: 'permissions', action: 'create', name: 'Create permissions', description: 'Allows creating permissions' },
  { code: 'iam.permissions.read', legacyCode: 'permissions.read', service: 'iam', resource: 'permissions', action: 'read', name: 'Read permissions', description: 'Allows viewing permissions' },
  { code: 'iam.permissions.update', legacyCode: 'permissions.update', service: 'iam', resource: 'permissions', action: 'update', name: 'Update permissions', description: 'Allows editing permissions' },
  { code: 'iam.permissions.delete', legacyCode: 'permissions.delete', service: 'iam', resource: 'permissions', action: 'delete', name: 'Delete permissions', description: 'Allows deleting permissions' },
  { code: 'iam.permission_groups.read', legacyCode: 'permission_groups.read', service: 'iam', resource: 'permission_groups', action: 'read', name: 'Read permission bundles', description: 'Allows viewing permission bundles' },
  { code: 'iam.permission_groups.manage', legacyCode: 'permission_groups.manage', service: 'iam', resource: 'permission_groups', action: 'manage', name: 'Manage permission bundles', description: 'Allows creating bundles and composing roles from them' },
  { code: 'iam.dashboard.admin', legacyCode: 'dashboard.admin', service: 'iam', resource: 'dashboard', action: 'admin', name: 'Dashboard admin', description: 'Access to the admin dashboard section' },
  { code: 'iam.dashboard.manager', legacyCode: 'dashboard.manager', service: 'iam', resource: 'dashboard', action: 'manager', name: 'Dashboard manager', description: 'Access to the manager dashboard section' },
  { code: 'iam.dashboard.operator', legacyCode: 'dashboard.operator', service: 'iam', resource: 'dashboard', action: 'operator', name: 'Dashboard operator', description: 'Access to the operator dashboard section' },
  { code: 'iam.dashboard.client', legacyCode: 'dashboard.client', service: 'iam', resource: 'dashboard', action: 'client', name: 'Dashboard client', description: 'Access to the client dashboard section' },
  { code: 'iam.dashboard.viewer', legacyCode: 'dashboard.viewer', service: 'iam', resource: 'dashboard', action: 'viewer', name: 'Dashboard viewer', description: 'Access to the viewer dashboard section' },
  { code: 'iam.dashboard.platform', legacyCode: 'dashboard.platform', service: 'iam', resource: 'dashboard', action: 'platform', name: 'Dashboard platform', description: 'Access to the platform tenant administration section' },
  { code: 'iam.system.settings', legacyCode: 'system.settings', service: 'iam', resource: 'system', action: 'settings', name: 'System settings', description: 'Allows managing system settings' },
  { code: 'platform.tenants.create', legacyCode: 'tenants.create', service: 'platform', resource: 'tenants', action: 'create', name: 'Create tenants', description: 'Allows creating tenants (platform)' },
  { code: 'platform.tenants.read', legacyCode: 'tenants.read', service: 'platform', resource: 'tenants', action: 'read', name: 'Read tenants', description: 'Allows listing tenants (platform)' },
  { code: 'platform.tenants.update', legacyCode: 'tenants.update', service: 'platform', resource: 'tenants', action: 'update', name: 'Update tenants', description: 'Allows renaming tenants (platform)' },
  { code: 'platform.tenants.activate', legacyCode: 'tenants.activate', service: 'platform', resource: 'tenants', action: 'activate', name: 'Activate tenants', description: 'Allows activating tenants (platform)' },
  { code: 'platform.tenants.deactivate', legacyCode: 'tenants.deactivate', service: 'platform', resource: 'tenants', action: 'deactivate', name: 'Deactivate tenants', description: 'Allows suspending tenants (platform)' },
  { code: 'platform.services.read', legacyCode: 'services.read', service: 'platform', resource: 'services', action: 'read', name: 'Read service catalog', description: 'Allows listing Hub services and tenant entitlements' },
  { code: 'platform.services.manage', legacyCode: 'services.manage', service: 'platform', resource: 'services', action: 'manage', name: 'Manage service entitlements', description: 'Allows enabling, suspending and quoting services per tenant' },
  { code: 'platform.usage.read', legacyCode: 'usage.read', service: 'platform', resource: 'usage', action: 'read', name: 'Read usage', description: 'Allows viewing the own tenant\'s metered usage' },
  { code: 'platform.usage.read_all', legacyCode: 'usage.read_all', service: 'platform', resource: 'usage', action: 'read_all', name: 'Read usage of every tenant', description: 'Allows viewing metered usage across tenants (platform)' },
  { code: 'iam.audit.read', legacyCode: 'audit.read', service: 'iam', resource: 'audit', action: 'read', name: 'Read audit events', description: 'Allows viewing the audit trail' },
  { code: 'iam.sessions.revoke', legacyCode: 'sessions.revoke', service: 'iam', resource: 'sessions', action: 'revoke', name: 'Revoke sessions', description: 'Allows revoking user sessions' },
  { code: 'iam.oauth_clients.create', legacyCode: 'oauth_clients.create', service: 'iam', resource: 'oauth_clients', action: 'create', name: 'Create OAuth clients', description: 'Allows registering OAuth/OIDC clients' },
  { code: 'iam.oauth_clients.read', legacyCode: 'oauth_clients.read', service: 'iam', resource: 'oauth_clients', action: 'read', name: 'Read OAuth clients', description: 'Allows listing OAuth/OIDC clients' },
  { code: 'iam.oauth_clients.update', legacyCode: 'oauth_clients.update', service: 'iam', resource: 'oauth_clients', action: 'update', name: 'Update OAuth clients', description: 'Allows updating OAuth/OIDC clients' },
  { code: 'iam.oauth_clients.delete', legacyCode: 'oauth_clients.delete', service: 'iam', resource: 'oauth_clients', action: 'delete', name: 'Delete OAuth clients', description: 'Allows deleting OAuth/OIDC clients' },
  { code: 'iam.service_accounts.create', legacyCode: 'service_accounts.create', service: 'iam', resource: 'service_accounts', action: 'create', name: 'Create service accounts', description: 'Allows creating non-human identities' },
  { code: 'iam.service_accounts.read', legacyCode: 'service_accounts.read', service: 'iam', resource: 'service_accounts', action: 'read', name: 'Read service accounts', description: 'Allows listing service accounts' },
  { code: 'iam.service_accounts.update', legacyCode: 'service_accounts.update', service: 'iam', resource: 'service_accounts', action: 'update', name: 'Update service accounts', description: 'Allows updating service accounts' },
  { code: 'iam.service_accounts.delete', legacyCode: 'service_accounts.delete', service: 'iam', resource: 'service_accounts', action: 'delete', name: 'Delete service accounts', description: 'Allows deleting service accounts' },
  { code: 'iam.api_keys.create', legacyCode: 'api_keys.create', service: 'iam', resource: 'api_keys', action: 'create', name: 'Create API keys', description: 'Allows issuing API keys' },
  { code: 'iam.api_keys.read', legacyCode: 'api_keys.read', service: 'iam', resource: 'api_keys', action: 'read', name: 'Read API keys', description: 'Allows listing API keys' },
  { code: 'iam.api_keys.delete', legacyCode: 'api_keys.delete', service: 'iam', resource: 'api_keys', action: 'delete', name: 'Delete API keys', description: 'Allows revoking API keys' },
  { code: 'iam.federation.create', legacyCode: 'federation.create', service: 'iam', resource: 'federation', action: 'create', name: 'Create identity providers', description: 'Allows configuring SSO/federation IdPs' },
  { code: 'iam.federation.read', legacyCode: 'federation.read', service: 'iam', resource: 'federation', action: 'read', name: 'Read identity providers', description: 'Allows listing SSO/federation IdPs' },
  { code: 'iam.federation.update', legacyCode: 'federation.update', service: 'iam', resource: 'federation', action: 'update', name: 'Update identity providers', description: 'Allows updating SSO/federation IdPs' },
  { code: 'iam.federation.delete', legacyCode: 'federation.delete', service: 'iam', resource: 'federation', action: 'delete', name: 'Delete identity providers', description: 'Allows removing SSO/federation IdPs' },
  { code: 'iam.policies.create', legacyCode: 'policies.create', service: 'iam', resource: 'policies', action: 'create', name: 'Create access policies', description: 'Allows creating ABAC/auth policies' },
  { code: 'iam.policies.read', legacyCode: 'policies.read', service: 'iam', resource: 'policies', action: 'read', name: 'Read access policies', description: 'Allows viewing ABAC/auth policies' },
  { code: 'iam.policies.update', legacyCode: 'policies.update', service: 'iam', resource: 'policies', action: 'update', name: 'Update access policies', description: 'Allows updating ABAC/auth policies' },
  { code: 'iam.policies.delete', legacyCode: 'policies.delete', service: 'iam', resource: 'policies', action: 'delete', name: 'Delete access policies', description: 'Allows deleting ABAC/auth policies' },
  { code: 'iam.scim.provision', legacyCode: 'scim.provision', service: 'iam', resource: 'scim', action: 'provision', name: 'SCIM provision', description: 'Allows SCIM user/group provisioning' },
  { code: 'iam.acl.read', legacyCode: 'acl.read', service: 'iam', resource: 'acl', action: 'read', name: 'Read resource ACLs', description: 'Allows viewing per-resource access control entries' },
  { code: 'iam.acl.grant', legacyCode: 'acl.grant', service: 'iam', resource: 'acl', action: 'grant', name: 'Grant resource ACLs', description: 'Allows creating per-resource allow/deny entries' },
  { code: 'iam.acl.revoke', legacyCode: 'acl.revoke', service: 'iam', resource: 'acl', action: 'revoke', name: 'Revoke resource ACLs', description: 'Allows removing per-resource access control entries' },
  { code: 'integration.integration.read', legacyCode: 'integration.read', service: 'integration', resource: 'integration', action: 'read', name: 'Read integrations', description: 'Allows viewing integrations' },
  { code: 'integration.integration.create', legacyCode: 'integration.create', service: 'integration', resource: 'integration', action: 'create', name: 'Create integrations', description: 'Allows creating integrations' },
  { code: 'integration.integration.update', legacyCode: 'integration.update', service: 'integration', resource: 'integration', action: 'update', name: 'Update integrations', description: 'Allows updating integrations' },
  { code: 'integration.integration.delete', legacyCode: 'integration.delete', service: 'integration', resource: 'integration', action: 'delete', name: 'Delete integrations', description: 'Allows deleting integrations' },
  { code: 'integration.integration.test', legacyCode: 'integration.test', service: 'integration', resource: 'integration', action: 'test', name: 'Test integrations', description: 'Allows testing integration connections' },
  { code: 'integration.integration.sync', legacyCode: 'integration.sync', service: 'integration', resource: 'integration', action: 'sync', name: 'Sync integrations', description: 'Allows running integration synchronization' },
  { code: 'integration.integration.read_logs', legacyCode: 'integration.read_logs', service: 'integration', resource: 'integration', action: 'read_logs', name: 'Read integration logs', description: 'Allows viewing integration sync/test logs' },
] as const

export interface PermissionBundleEntry {
  slug: string
  service: string
  name: string
  description: string
  codes: readonly string[]
}

export const PERMISSION_BUNDLES: readonly PermissionBundleEntry[] = [
  { slug: 'iam.admin', service: 'iam', name: 'IAM administration', description: 'Identity, RBAC and IAM platform administration', codes: ['iam.acl.grant', 'iam.acl.read', 'iam.acl.revoke', 'iam.api_keys.create', 'iam.api_keys.delete', 'iam.api_keys.read', 'iam.audit.read', 'iam.dashboard.admin', 'iam.federation.create', 'iam.federation.delete', 'iam.federation.read', 'iam.federation.update', 'iam.oauth_clients.create', 'iam.oauth_clients.delete', 'iam.oauth_clients.read', 'iam.oauth_clients.update', 'iam.permission_groups.manage', 'iam.permission_groups.read', 'iam.permissions.create', 'iam.permissions.delete', 'iam.permissions.read', 'iam.permissions.update', 'iam.policies.create', 'iam.policies.delete', 'iam.policies.read', 'iam.policies.update', 'iam.roles.assign', 'iam.roles.create', 'iam.roles.delete', 'iam.roles.read', 'iam.roles.update', 'iam.scim.provision', 'iam.service_accounts.create', 'iam.service_accounts.delete', 'iam.service_accounts.read', 'iam.service_accounts.update', 'iam.sessions.revoke', 'platform.usage.read', 'iam.users.assign', 'iam.users.create', 'iam.users.delete', 'iam.users.read', 'iam.users.update'] },
  { slug: 'iam.manager', service: 'iam', name: 'IAM manager', description: 'User oversight and read-only RBAC', codes: ['iam.dashboard.manager', 'iam.permissions.read', 'iam.roles.read', 'iam.users.read', 'iam.users.update'] },
  { slug: 'iam.operator', service: 'iam', name: 'IAM operator', description: 'Day-to-day operations', codes: ['iam.dashboard.operator', 'iam.users.read'] },
  { slug: 'iam.client', service: 'iam', name: 'IAM client', description: 'Own profile access only', codes: ['iam.dashboard.client'] },
  { slug: 'iam.viewer', service: 'iam', name: 'IAM viewer', description: 'Read-only system overview', codes: ['iam.dashboard.viewer', 'iam.permissions.read', 'iam.roles.read', 'iam.users.read'] },
  { slug: 'platform.admin', service: 'platform', name: 'Platform administration', description: 'Cross-tenant administration and system settings', codes: ['iam.dashboard.platform', 'platform.services.manage', 'platform.services.read', 'iam.system.settings', 'platform.tenants.activate', 'platform.tenants.create', 'platform.tenants.deactivate', 'platform.tenants.read', 'platform.tenants.update', 'platform.usage.read_all'] },
  { slug: 'integration.admin', service: 'integration', name: 'Integration administration', description: 'Full control over the integration hub', codes: ['integration.integration.create', 'integration.integration.delete', 'integration.integration.read', 'integration.integration.read_logs', 'integration.integration.sync', 'integration.integration.test', 'integration.integration.update'] },
] as const

const ALIASES: Record<string, readonly string[]> = PERMISSION_CATALOG.reduce(
  (acc, entry) => {
    const pair = [entry.code, entry.legacyCode] as const
    acc[entry.code] = pair
    acc[entry.legacyCode] = pair
    return acc
  },
  {} as Record<string, readonly string[]>,
)

/** Both accepted forms of a code (canonical + legacy), or the code itself. */
export function permissionAliases(code: string): readonly string[] {
  return ALIASES[code] ?? [code]
}

/** True when the granted set contains any accepted form of the code. */
export function hasPermissionCode(granted: ReadonlySet<string>, code: string): boolean {
  return permissionAliases(code).some((alias) => granted.has(alias))
}

export function permissionService(code: string): string {
  const parts = code.split('.')
  if (parts.length >= 3) return parts[0]
  return PERMISSION_CATALOG.find((entry) => entry.legacyCode === code)?.service ?? ''
}

export function permissionResource(code: string): string {
  const parts = code.split('.')
  if (parts.length >= 3) return parts[1]
  return parts.length === 2 ? parts[0] : code
}

export function permissionAction(code: string): string {
  const parts = code.split('.')
  if (parts.length >= 3) return parts.slice(2).join('.')
  return parts.length === 2 ? parts[1] : ''
}

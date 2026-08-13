import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { isClientMapHome } from '@/utils/homeRoute'
import type { MenuItem } from '@/components/layout/BaseSidebar.vue'

export interface NavMenuOption {
  label: string
  value: string
  icon: string
  path: string
}

export interface LayoutConfig {
  headerTitle: string
  userSubtitle: string
  menuItems: MenuItem[]
  navMenuOptions: NavMenuOption[]
}

function pathMatches(current: string, target: string): boolean {
  if (target === '/dashboard') {
    return current === '/dashboard' || current === '/'
  }
  if (target === '/main') {
    return current === '/main'
  }
  if (target.startsWith('/account')) {
    return current.startsWith('/account')
  }
  // Platform overview represents the platform section in the sidebar.
  if (target === '/platform') {
    return (
      current === '/platform' ||
      current === '/tenants' ||
      current.startsWith('/tenants/') ||
      current === '/integrations' ||
      current.startsWith('/integrations/')
    )
  }
  // Exact match only — avoids /reports activating on /reports/indicators
  return current === target
}

export function useLayoutConfig() {
  const route = useRoute()
  const auth = useAuthStore()
  const dashboard = useDashboardStore()
  const { can } = usePermissions()

  const layoutConfig = computed<LayoutConfig>(() => {
    const currentPath = route.path.replace(/\/$/, '') || '/'
    const roles = auth.user?.roleNames.join(' · ') || 'no role'
    const clientMap = isClientMapHome(auth.user?.permissions)
    const homePath = clientMap ? '/main' : '/dashboard'
    const homeLabel = clientMap ? 'Map' : 'Dashboard'
    const homeIcon = clientMap ? 'map' : 'dashboard'

    const menuItems: MenuItem[] = [
      {
        id: 'nav-home',
        label: homeLabel,
        icon: homeIcon,
        active: pathMatches(currentPath, homePath) || currentPath === '/',
        link: homePath,
      },
    ]

    for (const item of dashboard.menu) {
      if (!can(item.required_permission)) continue
      // Home entry already covers /main for CLIENT
      if (clientMap && item.route === '/main') continue
      menuItems.push({
        id: item.id,
        label: item.label,
        icon: item.icon,
        active: pathMatches(currentPath, item.route),
        link: item.route,
        required_permission: item.required_permission,
      })
    }

    if (can(PermissionCode.USERS_READ) || can(PermissionCode.DASHBOARD_CLIENT)) {
      menuItems.push({ id: 'divider-account', divider: true })
      menuItems.push({
        id: 'nav-account',
        label: 'My account',
        icon: 'manage_accounts',
        active: currentPath.startsWith('/account'),
        link: '/account/profile',
      })
      menuItems.push({
        id: 'nav-mfa',
        label: 'MFA setup',
        icon: 'phonelink_lock',
        active: currentPath.startsWith('/iam/mfa'),
        link: '/iam/mfa',
      })
    }

    if (can(PermissionCode.AUDIT_READ)) {
      menuItems.push({
        id: 'nav-audit',
        label: 'Audit',
        icon: 'policy',
        active: currentPath.startsWith('/iam/audit'),
        link: '/iam/audit',
        required_permission: PermissionCode.AUDIT_READ,
      })
    }
    if (can(PermissionCode.OAUTH_CLIENTS_READ)) {
      menuItems.push({
        id: 'nav-oauth',
        label: 'OAuth clients',
        icon: 'apps',
        active: currentPath.startsWith('/iam/oauth-clients'),
        link: '/iam/oauth-clients',
        required_permission: PermissionCode.OAUTH_CLIENTS_READ,
      })
    }

    const navMenuOptions: NavMenuOption[] = [
      {
        label: homeLabel,
        value: clientMap ? 'main' : 'dashboard',
        icon: homeIcon,
        path: homePath,
      },
    ]

    if (can(PermissionCode.DASHBOARD_ADMIN)) {
      navMenuOptions.push({
        label: 'Administration',
        value: 'admin',
        icon: 'admin_panel_settings',
        path: '/admin',
      })
    }
    if (can(PermissionCode.USERS_READ)) {
      navMenuOptions.push({
        label: 'Users',
        value: 'users',
        icon: 'people',
        path: '/users',
      })
    }
    if (can(PermissionCode.ROLES_READ)) {
      navMenuOptions.push({
        label: 'Roles',
        value: 'roles',
        icon: 'shield',
        path: '/roles',
      })
    }
    if (can(PermissionCode.PERMISSIONS_READ)) {
      navMenuOptions.push({
        label: 'Permissions',
        value: 'permissions',
        icon: 'key',
        path: '/permissions',
      })
    }
    if (can(PermissionCode.DASHBOARD_MANAGER)) {
      navMenuOptions.push({
        label: 'Indicators',
        value: 'indicators',
        icon: 'insights',
        path: '/reports/indicators',
      })
      navMenuOptions.push({
        label: 'Reports',
        value: 'reports',
        icon: 'description',
        path: '/reports',
      })
    }
    if (can(PermissionCode.DASHBOARD_OPERATOR)) {
      navMenuOptions.push({
        label: 'Operations',
        value: 'operations',
        icon: 'task_alt',
        path: '/operations/today',
      })
    }
    if (can(PermissionCode.DASHBOARD_CLIENT) && !clientMap) {
      navMenuOptions.push({
        label: 'Map',
        value: 'main',
        icon: 'map',
        path: '/main',
      })
    }
    if (can(PermissionCode.DASHBOARD_CLIENT)) {
      navMenuOptions.push({
        label: 'My data',
        value: 'me',
        icon: 'person',
        path: '/me',
      })
    }
    if (can(PermissionCode.DASHBOARD_VIEWER)) {
      navMenuOptions.push({
        label: 'Read-only view',
        value: 'readonly',
        icon: 'visibility',
        path: '/dashboard/readonly',
      })
    }

    const activeNav = navMenuOptions.find((opt) => pathMatches(currentPath, opt.path))
    const activeMenu = menuItems.find((item) => item.active && !item.divider)

    return {
      headerTitle: activeNav?.label || activeMenu?.label || 'Lanstar',
      userSubtitle: roles,
      menuItems,
      navMenuOptions,
    }
  })

  return { layoutConfig }
}

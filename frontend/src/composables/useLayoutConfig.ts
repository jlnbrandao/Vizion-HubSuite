import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNavigationStore } from '@/stores/navigation'
import type { MenuItem } from '@/components/layout/BaseSidebar.vue'
import type { NavigationItemResponse } from '@/types/api'

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

/** Order of the sidebar sections; unknown groups are appended in catalog order. */
const GROUP_ORDER = [
  'overview',
  'workspace',
  'administration',
  'security',
  'platform',
  'account',
] as const

function pathMatches(current: string, target: string): boolean {
  if (target === '/dashboard') {
    return current === '/dashboard' || current === '/'
  }
  if (target.startsWith('/account')) {
    return current.startsWith('/account')
  }
  // Exact match only — avoids /reports activating on /reports/indicators
  return current === target
}

function groupRank(group: string): number {
  const index = GROUP_ORDER.indexOf(group as (typeof GROUP_ORDER)[number])
  return index === -1 ? GROUP_ORDER.length : index
}

export function useLayoutConfig() {
  const route = useRoute()
  const auth = useAuthStore()
  const navigation = useNavigationStore()

  onMounted(() => {
    void navigation.ensureLoaded()
  })

  const layoutConfig = computed<LayoutConfig>(() => {
    const currentPath = route.path.replace(/\/$/, '') || '/'
    const roles = auth.user?.roleNames.join(' · ') || 'no role'

    const ordered = [...navigation.items].sort(
      (a, b) => groupRank(a.group) - groupRank(b.group),
    )

    const menuItems: MenuItem[] = []
    let previousGroup: string | null = null
    for (const item of ordered) {
      if (previousGroup !== null && item.group !== previousGroup) {
        menuItems.push({ id: `divider-${item.group}`, divider: true })
      }
      previousGroup = item.group
      menuItems.push({
        id: item.id,
        label: item.label,
        icon: item.icon,
        active: pathMatches(currentPath, item.route),
        link: item.route,
        ...(item.permission ? { required_permission: item.permission } : {}),
      })
    }

    const navMenuOptions: NavMenuOption[] = navigation.quickItems.map(
      (item: NavigationItemResponse) => ({
        label: item.label,
        value: item.id,
        icon: item.icon,
        path: item.route,
      }),
    )

    const activeNav = navMenuOptions.find((opt) => pathMatches(currentPath, opt.path))
    const activeMenu = menuItems.find((item) => item.active && !item.divider)

    return {
      headerTitle: activeNav?.label || activeMenu?.label || 'Vizion',
      userSubtitle: roles,
      menuItems,
      navMenuOptions,
    }
  })

  return { layoutConfig }
}

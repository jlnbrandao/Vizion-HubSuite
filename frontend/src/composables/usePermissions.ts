import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { PermissionCodeValue } from '@/constants/permissions'

/**
 * Clean permission API for the UI — no role-name branching.
 * Screens call can() / canAny() / canAll(); templates use v-if="can(...)".
 */
export function usePermissions() {
  const auth = useAuthStore()

  const permissions = computed(() => new Set(auth.user?.permissions ?? []))
  const roles = computed(() => new Set(auth.user?.roleNames ?? []))

  function can(code: PermissionCodeValue | string): boolean {
    return permissions.value.has(code)
  }

  function canAny(...codes: Array<PermissionCodeValue | string>): boolean {
    return codes.some((code) => permissions.value.has(code))
  }

  function canAll(...codes: Array<PermissionCodeValue | string>): boolean {
    return codes.every((code) => permissions.value.has(code))
  }

  function hasRole(name: string): boolean {
    return roles.value.has(name.toUpperCase())
  }

  return {
    permissions,
    roles,
    can,
    canAny,
    canAll,
    hasRole,
  }
}

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import AccountModal from '@/components/layout/AccountModal.vue'
import { useMaps, type MapLayerType } from '@/composables/useMaps'
import { usePermissions } from '@/composables/usePermissions'
import { usePlatform } from '@/composables/usePlatform'
import { PermissionCode } from '@/constants/permissions'
import { useAuthStore } from '@/stores/auth'
import logoColor from '@/assets/brand/logo-color.png'
import defaultIcon from '@/assets/icons/default.svg'

interface Area {
  id: number
  name: string
  status: 'online' | 'offline' | 'unknown'
  category?: string
  lat: number
  lng: number
  lastSeen: Date | null
  attributes?: Record<string, unknown>
}

const labels = {
  searchArea: 'Search area',
  hideAreaList: 'Hide area list',
  showAreaList: 'Show area list',
  filterAreas: 'Filter areas',
  addNewArea: 'Add new area',
  accountProfile: 'Account profile',
  areasManage: 'Manage areas',
  unpinAreaList: 'Unpin area list',
  pinAreaList: 'Pin area list',
  noPosition: 'No position',
  online: 'Online',
  unknown: 'Unknown ({time})',
  offline: 'Offline ({time})',
  dashboard: 'Dashboard',
  notifications: 'Notifications',
  reports: 'Reports',
  settings: 'Settings',
  account: 'Account',
  profileOf: '{name} profile',
  locate: 'Locate',
  zoomIn: 'Zoom in',
  zoomOut: 'Zoom out',
  locationiqStreets: 'LocationIQ Streets',
  cartodbStreets: 'CartoDB Streets',
  openStreetMap: 'OpenStreetMap',
  satellite: 'Satellite',
  whatsapp: 'WhatsApp',
  email: 'Email',
  getInTouch: 'Get in touch',
  loadingMap: 'Loading map...',
} as const

const authStore = useAuthStore()
const router = useRouter()
const $q = useQuasar()
const { isWeb } = usePlatform()
const { canAny } = usePermissions()

const {
  initMap,
  updateMarkerSelection,
  setView,
  changeLayer,
  forceMarkerSync,
  destroy,
  leafletMap,
  currentLayer: mapCurrentLayer,
} = useMaps()

const areas = ref<Area[]>([])
const selectedArea = ref<Area | null>(null)
const searchQuery = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const showAccountModal = ref(false)

const isAreaListVisible = ref(false)
const isAreaListPinned = ref(false)
const isLayerMenuOpen = ref(false)
const isOptionsMenuOpen = ref(false)

const screenWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)
const isLarge = computed(() => screenWidth.value >= 1024)

const floatingButtonsScrollRef = ref<HTMLElement | null>(null)
const buttonsContainer = ref<HTMLElement | null>(null)
const canScrollFloatingLeft = ref(false)
const canScrollFloatingRight = ref(false)

const userDisplayName = computed(() => authStore.user?.fullName || 'User')

const mainSearchPlaceholder = computed(() => labels.searchArea)

const areaListToggleTitle = computed(() =>
  isAreaListVisible.value ? labels.hideAreaList : labels.showAreaList,
)

const areaListPinTitle = computed(() =>
  isAreaListPinned.value ? labels.unpinAreaList : labels.pinAreaList,
)

const profileOfTitle = computed(() =>
  labels.profileOf.replace('{name}', userDisplayName.value),
)

const filteredAreas = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return areas.value
  return areas.value.filter((area) => area.name.toLowerCase().includes(query))
})

const hasAnyQuickActionPermission = computed(() => canAccessComponent('main-get-in-touch-btn'))

/**
 * The map is the placeholder for the future geo service slice, so its widgets
 * borrow IAM dashboard codes: a client sees and manages their own areas, while
 * the cross-tenant management screen stays with admin/manager profiles.
 * Unknown codes are denied — a new widget must declare its permission here.
 */
const COMPONENT_VIEW_PERMISSIONS: Record<string, readonly string[]> = {
  'main-get-in-touch-btn': [PermissionCode.DASHBOARD_CLIENT],
  'main-filter-areas-btn': [PermissionCode.DASHBOARD_CLIENT],
  'main-add-area-btn': [PermissionCode.DASHBOARD_CLIENT, PermissionCode.DASHBOARD_ADMIN],
  'main-area-manage': [
    PermissionCode.DASHBOARD_CLIENT,
    PermissionCode.DASHBOARD_MANAGER,
    PermissionCode.DASHBOARD_ADMIN,
  ],
}

const COMPONENT_EDIT_PERMISSIONS: Record<string, readonly string[]> = {
  ...COMPONENT_VIEW_PERMISSIONS,
  'main-area-manage': [PermissionCode.DASHBOARD_MANAGER, PermissionCode.DASHBOARD_ADMIN],
}

function canAccessComponent(code: string): boolean {
  return canAny(...(COMPONENT_VIEW_PERMISSIONS[code] ?? []))
}

function canEdit(_type: string, code: string): boolean {
  return canAny(...(COMPONENT_EDIT_PERMISSIONS[code] ?? []))
}

function formatTimeSince(lastUpdate: string): string {
  if (!lastUpdate) return 'unknown'
  const last = new Date(lastUpdate)
  const now = new Date()
  const diffMs = now.getTime() - last.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins} min ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours} h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`
}

function getLastUpdateTime(area: Area): string {
  if (area.status === 'offline' || area.status === 'unknown') {
    const lastUpdate = area.attributes?.lastUpdate
    return (typeof lastUpdate === 'string' ? lastUpdate : '') || area.lastSeen?.toISOString() || ''
  }
  return area.lastSeen?.toISOString() || ''
}

function getAreaStatusText(area: Area): string {
  if (!area.lat || !area.lng || area.lat === 0 || area.lng === 0) {
    return labels.noPosition
  }
  if (area.status === 'online') return labels.online
  const time = formatTimeSince(getLastUpdateTime(area))
  if (area.status === 'unknown') {
    return labels.unknown.replace('{time}', time)
  }
  return labels.offline.replace('{time}', time)
}

function getAreaIcon(_area: Area): string {
  return defaultIcon
}

function getBlockedIcon(area: Area): string {
  const blocked = area.attributes?.blocked
  if (blocked === true || blocked === 'true' || blocked === 1) return 'lock'
  return 'lock_open'
}

function getBlockedIconClass(area: Area): string {
  const blocked = area.attributes?.blocked
  if (blocked === true || blocked === 'true' || blocked === 1) return 'text-red-600'
  return 'text-gray-400'
}

function getEngineIconClass(area: Area): string {
  const ignition = area.attributes?.ignition
  if (ignition === true || ignition === 'true' || ignition === 1) return 'text-green-600'
  return 'text-gray-400'
}

function getBatteryLevel(area: Area): number | null {
  const batteryLevel = area.attributes?.batteryLevel
  if (batteryLevel === undefined || batteryLevel === null) return null
  const level = typeof batteryLevel === 'string' ? parseFloat(batteryLevel) : Number(batteryLevel)
  return Number.isFinite(level) ? level : null
}

function getBatteryIcon(area: Area): string {
  const batteryLevel = getBatteryLevel(area)
  const isCharging =
    area.attributes?.charge === true ||
    area.attributes?.charge === 'true' ||
    area.attributes?.charge === 1

  if (batteryLevel === null) return 'battery_unknown'
  if (isCharging) {
    if (batteryLevel > 70) return 'battery_charging_full'
    if (batteryLevel > 30) return 'battery_charging_60'
    return 'battery_charging_20'
  }
  if (batteryLevel > 70) return 'battery_full'
  if (batteryLevel > 30) return 'battery_6_bar'
  return 'battery_2_bar'
}

function getBatteryIconClass(area: Area): string {
  const batteryLevel = getBatteryLevel(area)
  if (batteryLevel === null) return 'text-gray-400'
  if (batteryLevel > 70) return 'text-green-600'
  if (batteryLevel > 30) return 'text-yellow-600'
  return 'text-red-600'
}

async function focusOnArea(area: Area) {
  if (!area.lat || !area.lng || area.lat === 0 || area.lng === 0) return

  if (selectedArea.value && selectedArea.value.id !== area.id) {
    updateMarkerSelection(String(selectedArea.value.id), false)
  }

  selectedArea.value = area
  updateMarkerSelection(String(area.id), true)
  await setView({ lat: area.lat, lng: area.lng }, 15)
}

function toggleAreaList(): void {
  if (isAreaListPinned.value && isAreaListVisible.value) return
  isAreaListVisible.value = !isAreaListVisible.value
}

function showAreaList(): void {
  if (!isAreaListVisible.value) {
    isAreaListVisible.value = true
  }
}

function toggleAreaListPin(): void {
  isAreaListPinned.value = !isAreaListPinned.value
}

function toggleFilters(): void {
  $q.notify({ type: 'info', message: 'Area filters coming soon', position: 'top', timeout: 1500 })
}

function addNewArea(): void {
  $q.notify({ type: 'info', message: 'Add new area', position: 'top', timeout: 1500 })
}

function navigateToAreasManage(): void {
  $q.notify({ type: 'info', message: 'Area management coming soon', position: 'top', timeout: 1500 })
}

function handleResize(): void {
  if (typeof window !== 'undefined') {
    screenWidth.value = window.innerWidth
  }
  void nextTick(() => {
    updateFloatingButtonsScrollState()
  })
}

function handleFloatingStripScroll(): void {
  updateFloatingButtonsScrollState()
}

function updateFloatingButtonsScrollState(): void {
  const scrollEl = floatingButtonsScrollRef.value
  if (!scrollEl) {
    canScrollFloatingLeft.value = false
    canScrollFloatingRight.value = false
    return
  }

  const overflow = scrollEl.scrollWidth > scrollEl.clientWidth + 1
  canScrollFloatingLeft.value = overflow && scrollEl.scrollLeft > 1
  canScrollFloatingRight.value =
    overflow && scrollEl.scrollLeft + scrollEl.clientWidth < scrollEl.scrollWidth - 1
}

const showLeftNavButton = computed(() => canScrollFloatingLeft.value)
const showRightNavButton = computed(() => canScrollFloatingRight.value)

function scrollLeft(): void {
  floatingButtonsScrollRef.value?.scrollBy({ left: -200, behavior: 'smooth' })
}

function scrollRight(): void {
  floatingButtonsScrollRef.value?.scrollBy({ left: 200, behavior: 'smooth' })
}

function handleFloatingBtnClick(route: string): void {
  switch (route) {
    case 'dashboard':
      $q.notify({ type: 'info', message: 'Dashboard coming soon', position: 'top', timeout: 1500 })
      break
    case 'notifications':
      $q.notify({ type: 'info', message: 'Notifications coming soon', position: 'top', timeout: 1500 })
      break
    case 'reports':
      $q.notify({ type: 'info', message: 'Reports coming soon', position: 'top', timeout: 1500 })
      break
    case 'settings':
      $q.notify({ type: 'info', message: 'Settings coming soon', position: 'top', timeout: 1500 })
      break
    case 'account':
      void router.push({ name: 'account-profile' })
      break
    default:
      break
  }
}

function onFloatingBtnTouchStart(_event: TouchEvent): void {}

function onFloatingBtnTap(route: string, _event: TouchEvent): void {
  handleFloatingBtnClick(route)
}

function handleZoomIn(): void {
  if (leafletMap.value) {
    leafletMap.value.zoomIn()
    setTimeout(() => forceMarkerSync(), 0)
  }
}

function handleZoomOut(): void {
  if (leafletMap.value) {
    leafletMap.value.zoomOut()
    setTimeout(() => forceMarkerSync(), 0)
  }
}

async function handleLocate(): Promise<void> {
  if (typeof navigator === 'undefined' || !navigator.geolocation) {
    error.value = 'Geolocation is not supported in this browser.'
    return
  }

  try {
    const position = await new Promise<GeolocationPosition>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      })
    })

    const lat = position.coords.latitude
    const lng = position.coords.longitude
    await setView({ lat, lng }, 15)
  } catch {
    error.value = 'Unable to get your location.'
    setTimeout(() => {
      error.value = null
    }, 4000)
  }
}

function toggleLayerMenu(): void {
  isLayerMenuOpen.value = !isLayerMenuOpen.value
  if (isOptionsMenuOpen.value) {
    isOptionsMenuOpen.value = false
  }
}

function selectLayer(layerType: MapLayerType): void {
  changeLayer(layerType)
  isLayerMenuOpen.value = false
}

function toggleOptionsMenu(): void {
  isOptionsMenuOpen.value = !isOptionsMenuOpen.value
  if (isLayerMenuOpen.value) {
    isLayerMenuOpen.value = false
  }
}

function handleWhatsApp(): void {
  isOptionsMenuOpen.value = false
}

function handleEmail(): void {
  isOptionsMenuOpen.value = false
  window.location.href = 'mailto:contact@example.com?subject=Contact'
}

function handleClickOutside(event: Event): void {
  const target = event.target as HTMLElement
  const isInsideFloatingSearch = target.closest('.floating-search')
  const isInsideLayerMenu =
    target.closest('.layer-menu-container') || target.closest('.layer-menu-dropdown')
  const isInsideOptionsMenu =
    target.closest('.options-menu-container') || target.closest('.options-badges-container')
  const isOnMap = target.id === 'map' || target.closest('#map')

  if (!isInsideFloatingSearch) {
    if (isAreaListVisible.value && !isAreaListPinned.value) {
      isAreaListVisible.value = false
    }
  }

  if (!isInsideLayerMenu && isLayerMenuOpen.value) {
    isLayerMenuOpen.value = false
  }

  if ((!isInsideOptionsMenu || isOnMap) && isOptionsMenuOpen.value) {
    isOptionsMenuOpen.value = false
  }
}

watch([buttonsContainer, isLarge], () => {
  void nextTick(() => {
    updateFloatingButtonsScrollState()
  })
})

watch(screenWidth, () => {
  void nextTick(() => {
    updateFloatingButtonsScrollState()
  })
})

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  document.addEventListener('click', handleClickOutside)

  loading.value = true
  error.value = null

  try {
    await nextTick()
    await initMap('map')
    areas.value = []
    await nextTick()
    leafletMap.value?.invalidateSize()
  } catch (err) {
    console.error('[MainPage] map init failed', err)
    error.value = 'Failed to load the map.'
  } finally {
    loading.value = false
    await nextTick()
    leafletMap.value?.invalidateSize()
    updateFloatingButtonsScrollState()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('click', handleClickOutside)
  destroy()
})
</script>

<template>
  <div
    class="main-page h-screen w-screen m-0 p-0 overflow-hidden relative"
    style="background-color: var(--app-navigation-background, #f9fafb)"
  >
    <div class="main-page-shell absolute inset-0 overflow-hidden">
      <!-- Map container must stay empty — Leaflet owns this DOM node -->
      <div
        id="map"
        class="main-page-map absolute inset-0 w-full h-full bg-gray-200 z-0"
        style="position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; background: #e5e7eb"
      />

      <!-- Loading overlay (sibling of #map so Vue never patches Leaflet DOM) -->
      <div
        v-if="loading"
        class="absolute inset-0 bg-white bg-opacity-80 flex flex-col items-center justify-center z-[1000]"
      >
        <q-spinner size="50px" color="primary" />
        <div class="mt-2 text-gray-600 text-sm">{{ labels.loadingMap }}</div>
      </div>

      <!-- Error message -->
      <div
        v-if="error"
        class="absolute bottom-5 left-1/2 transform -translate-x-1/2 bg-red-600 text-white rounded-full z-[1000] text-sm flex items-center"
        style="height: 2.5rem; padding: 0 0.75rem"
      >
        <q-icon name="error" size="20px" class="mr-2" />
        {{ error }}
      </div>

      <!-- Asset Search Input -->
      <div
        class="floating-search"
        :class="{
          'w-auto': !isLarge,
          'w-96 max-w-[calc(100vw-2rem)]': isLarge,
        }"
      >
        <div class="search-container">
          <div class="search-input-wrapper">
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="mainSearchPlaceholder"
              class="areas-search"
              :class="{
                'rounded-t-[15px] rounded-b-none border-b-0': isAreaListVisible,
              }"
              @click="showAreaList"
            />
            <div class="search-icons">
              <button
                type="button"
                class="search-icon-btn"
                :title="areaListToggleTitle"
                :class="{ muted: isAreaListPinned && isAreaListVisible }"
                :disabled="isAreaListPinned && isAreaListVisible"
                @click="toggleAreaList"
              >
                <q-icon name="menu" size="18px" />
              </button>
              <button
                v-if="canAccessComponent('main-filter-areas-btn')"
                type="button"
                class="search-icon-btn"
                :title="labels.filterAreas"
                :class="{
                  'cursor-not-allowed opacity-50': !canEdit('component', 'main-filter-areas-btn'),
                }"
                :disabled="!canEdit('component', 'main-filter-areas-btn')"
                @click="toggleFilters"
              >
                <q-icon name="filter_list" size="18px" />
              </button>
              <button
                v-if="canAccessComponent('main-add-area-btn')"
                type="button"
                class="search-icon-btn"
                :title="labels.addNewArea"
                :class="{
                  'cursor-not-allowed opacity-50': !canEdit('component', 'main-add-area-btn'),
                }"
                :disabled="!canEdit('component', 'main-add-area-btn')"
                @click="addNewArea"
              >
                <q-icon name="add" size="18px" />
              </button>
              <button
                v-if="!isLarge"
                type="button"
                class="search-icon-btn search-icon-btn-avatar"
                :title="labels.accountProfile"
                @click="showAccountModal = true"
              >
                <q-icon name="person" size="22px" class="text-gray-700" />
              </button>
            </div>
          </div>

          <!-- Asset List Panel -->
          <div
            v-show="isAreaListVisible"
            class="area-list"
            :class="{
              show: isAreaListVisible,
              'w-auto': !isLarge,
              'w-96 max-w-[calc(100vw-2rem)]': isLarge,
            }"
          >
            <div class="area-list-content">
              <ul class="list-unstyled mb-0 pb-0">
                <li
                  v-for="area in filteredAreas"
                  :key="area.id"
                  class="area-item"
                  :class="{ selected: selectedArea?.id === area.id }"
                  @click="focusOnArea(area)"
                >
                  <div class="flex items-center justify-between w-full">
                    <div class="flex items-center flex-1 min-w-0">
                      <div class="flex-shrink-0 mr-3">
                        <div
                          class="w-10 h-10 rounded-full border-2 border-gray-200 flex items-center justify-center shadow-md bg-white"
                        >
                          <img
                            :src="getAreaIcon(area)"
                            :alt="area.name"
                            class="area-icon-colored"
                            :style="{
                              width: '18px',
                              height: '18px',
                              filter:
                                'brightness(0) saturate(100%) invert(75%) sepia(0%) saturate(0%) hue-rotate(0deg) brightness(100%) contrast(100%)',
                            }"
                          />
                        </div>
                      </div>

                      <div class="flex-1 min-w-0">
                        <div class="text-gray-900 text-sm mb-1 truncate">{{ area.name }}</div>
                        <div
                          class="area-status text-xs truncate"
                          :class="{
                            'text-gray-300':
                              !area.lat || !area.lng || area.lat === 0 || area.lng === 0,
                            'text-green-600': area.status === 'online',
                            'text-red-600': area.status === 'offline',
                            'text-yellow-600': area.status === 'unknown',
                          }"
                        >
                          {{ getAreaStatusText(area) }}
                        </div>
                      </div>
                    </div>

                    <div class="flex-shrink-0 ml-4 flex items-center gap-3">
                      <q-icon
                        :name="getBlockedIcon(area)"
                        size="16px"
                        :class="getBlockedIconClass(area)"
                      />
                      <q-icon name="power" size="16px" :class="getEngineIconClass(area)" />
                      <q-icon
                        :name="getBatteryIcon(area)"
                        size="16px"
                        :class="getBatteryIconClass(area)"
                      />
                    </div>
                  </div>
                </li>
              </ul>
            </div>

            <div class="area-list-footer">
              <a
                v-if="canAccessComponent('main-area-manage')"
                href="#"
                class="areas-manage-link"
                :class="{
                  'cursor-not-allowed opacity-50 pointer-events-none': !canEdit(
                    'component',
                    'main-area-manage',
                  ),
                }"
                @click.prevent="
                  canEdit('component', 'main-area-manage') ? navigateToAreasManage() : null
                "
              >
                <q-icon name="settings" size="16px" class="mr-2" />
                <span>{{ labels.areasManage }}</span>
              </a>
              <div class="pin-icon-container">
                <button
                  type="button"
                  class="pin-icon-btn"
                  :title="areaListPinTitle"
                  @click="toggleAreaListPin"
                >
                  <q-icon
                    name="push_pin"
                    size="18px"
                    :class="{
                      'text-blue-600': isAreaListPinned,
                      'pin-icon-diagonal': !isAreaListPinned,
                    }"
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Floating Action Buttons with Swipe -->
      <div
        class="floating-buttons-shell"
        :class="{
          'w-auto': !isLarge,
          'w-96 max-w-[calc(100vw-2rem)]': isLarge,
        }"
      >
        <button
          v-if="isLarge && showLeftNavButton"
          type="button"
          class="floating-nav-button floating-nav-button-left"
          @click="scrollLeft"
        >
          <q-icon name="chevron_left" size="20px" class="text-gray-600" />
        </button>

        <div
          ref="floatingButtonsScrollRef"
          class="floating-buttons-container"
          @scroll.passive="handleFloatingStripScroll"
        >
          <div ref="buttonsContainer" class="floating-buttons-wrapper">
            <button
              v-if="canAccessComponent('main-dashboard-btn')"
              type="button"
              class="floating-btn-item"
              @click.stop="handleFloatingBtnClick('dashboard')"
              @touchstart.passive="onFloatingBtnTouchStart"
              @touchend.stop="onFloatingBtnTap('dashboard', $event)"
            >
              <q-icon name="dashboard" size="18px" class="text-gray-700" />
              <span class="text-sm font-normal text-gray-700">{{ labels.dashboard }}</span>
            </button>

            <button
              v-if="canAccessComponent('main-notifications-btn')"
              type="button"
              class="floating-btn-item"
              @click.stop="handleFloatingBtnClick('notifications')"
              @touchstart.passive="onFloatingBtnTouchStart"
              @touchend.stop="onFloatingBtnTap('notifications', $event)"
            >
              <q-icon name="notifications" size="18px" class="text-gray-700" />
              <span class="text-sm font-normal text-gray-700">{{ labels.notifications }}</span>
            </button>

            <button
              v-if="canAccessComponent('main-reports-btn')"
              type="button"
              class="floating-btn-item"
              @click.stop="handleFloatingBtnClick('reports')"
              @touchstart.passive="onFloatingBtnTouchStart"
              @touchend.stop="onFloatingBtnTap('reports', $event)"
            >
              <q-icon name="description" size="18px" class="text-gray-700" />
              <span class="text-sm font-normal text-gray-700">{{ labels.reports }}</span>
            </button>

            <button
              v-if="canAccessComponent('main-settings-btn')"
              type="button"
              class="floating-btn-item"
              @click.stop="handleFloatingBtnClick('settings')"
              @touchstart.passive="onFloatingBtnTouchStart"
              @touchend.stop="onFloatingBtnTap('settings', $event)"
            >
              <q-icon name="settings" size="18px" class="text-gray-700" />
              <span class="text-sm font-normal text-gray-700">{{ labels.settings }}</span>
            </button>

            <button
              v-if="canAccessComponent('main-account-btn')"
              type="button"
              class="floating-btn-item"
              @click.stop="handleFloatingBtnClick('account')"
              @touchstart.passive="onFloatingBtnTouchStart"
              @touchend.stop="onFloatingBtnTap('account', $event)"
            >
              <q-icon name="account_circle" size="18px" class="text-gray-700" />
              <span class="text-sm font-normal text-gray-700">{{ labels.account }}</span>
            </button>
          </div>
        </div>

        <button
          v-if="isLarge && showRightNavButton"
          type="button"
          class="floating-nav-button floating-nav-button-right"
          @click="scrollRight"
        >
          <q-icon name="chevron_right" size="20px" class="text-gray-600" />
        </button>
      </div>

      <!-- User Profile Button (xl) -->
      <button
        type="button"
        class="main-page-profile-btn absolute right-5 z-[1000] hidden xl:block w-14 h-14 rounded-full border-4 border-white cursor-pointer transition-all duration-300 hover:shadow-xl flex items-center justify-center"
        :style="{
          backgroundColor: '#f9fafb',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        }"
        @click="showAccountModal = true"
      >
        <q-icon name="person" size="26px" class="text-gray-700" />
      </button>

      <!-- Bottom Left: Company Logo -->
      <div class="absolute z-[1000] main-page-logo-wrap">
        <div class="relative tenant-logo-display-slot bg-transparent overflow-hidden">
          <img :src="logoColor" alt="Company Logo" class="w-full h-full object-contain object-bottom" />
        </div>
      </div>

      <!-- User Profile Section (Top Right) - Large viewports only -->
      <div
        v-if="isLarge"
        class="main-page-profile-section absolute right-4 z-[1000] flex items-center gap-3"
      >
        <div
          class="hidden sm:block bg-white rounded-full px-4 py-2 shadow-lg border border-gray-200"
        >
          <div class="flex items-center gap-2">
            <q-icon name="person" size="16px" class="text-gray-600" />
            <span class="text-sm font-medium text-gray-700">{{ userDisplayName }}</span>
          </div>
        </div>

        <button
          type="button"
          class="w-12 h-12 rounded-full border-4 border-white shadow-lg cursor-pointer transition-all duration-300 hover:shadow-xl flex items-center justify-center"
          :style="{
            backgroundColor: '#f9fafb',
            boxShadow: '0 8px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -5px rgba(0, 0, 0, 0.04)',
          }"
          :title="profileOfTitle"
          @click="showAccountModal = true"
        >
          <q-icon name="person" size="24px" class="text-gray-700" />
        </button>
      </div>

      <!-- Map Controls (Large screens) -->
      <div
        v-if="isWeb && isLarge"
        v-show="!isOptionsMenuOpen"
        class="absolute right-6 z-[1000] flex flex-col gap-2"
        style="bottom: calc(20px + 40px + 8px + 32px + 8px)"
      >
        <button
          type="button"
          class="w-8 h-8 bg-white rounded-full cursor-pointer flex items-center justify-center map-control-btn"
          :title="labels.locate"
          @click="handleLocate"
        >
          <q-icon name="my_location" size="18px" class="text-gray-700" />
        </button>

        <div class="w-8 flex flex-col rounded-full overflow-hidden map-control-zoom-container">
          <button
            type="button"
            class="w-full h-8 bg-white cursor-pointer flex items-center justify-center map-control-zoom-btn map-control-zoom-btn--top"
            :title="labels.zoomIn"
            @click="handleZoomIn"
          >
            <q-icon name="add" size="16px" class="text-gray-700" />
          </button>
          <button
            type="button"
            class="w-full h-8 bg-white cursor-pointer flex items-center justify-center map-control-zoom-btn"
            :title="labels.zoomOut"
            @click="handleZoomOut"
          >
            <q-icon name="remove" size="16px" class="text-gray-700" />
          </button>
        </div>
      </div>

      <!-- Layer Selector (Large screens) -->
      <div
        v-if="isWeb && isLarge"
        v-show="!isOptionsMenuOpen"
        class="layer-menu-container absolute right-6 z-[1000]"
        style="bottom: calc(20px + 40px + 8px)"
      >
        <button
          type="button"
          class="w-8 h-8 bg-white rounded-full cursor-pointer flex items-center justify-center map-control-btn"
          :class="{ 'map-control-btn--active': isLayerMenuOpen }"
          @click="toggleLayerMenu"
        >
          <q-icon name="layers" size="18px" class="text-gray-700" />
        </button>

        <div
          v-show="isLayerMenuOpen"
          class="layer-menu-dropdown absolute bottom-10 right-0 bg-white py-0 min-w-[160px] z-[1001]"
        >
          <button
            type="button"
            class="w-full px-4 py-2 text-left rounded-none"
            :class="{ 'layer-menu-dropdown__item--active': mapCurrentLayer === 'locationiq' }"
            @click="selectLayer('locationiq')"
          >
            <span
              class="text-sm"
              :class="
                mapCurrentLayer === 'locationiq'
                  ? 'font-semibold text-black'
                  : 'font-normal text-gray-700'
              "
              >{{ labels.locationiqStreets }}</span
            >
          </button>
          <button
            type="button"
            class="w-full px-4 py-2 text-left rounded-none"
            :class="{ 'layer-menu-dropdown__item--active': mapCurrentLayer === 'cartodb' }"
            @click="selectLayer('cartodb')"
          >
            <span
              class="text-sm"
              :class="
                mapCurrentLayer === 'cartodb'
                  ? 'font-semibold text-black'
                  : 'font-normal text-gray-700'
              "
              >{{ labels.cartodbStreets }}</span
            >
          </button>
          <button
            type="button"
            class="w-full px-4 py-2 text-left rounded-none"
            :class="{ 'layer-menu-dropdown__item--active': mapCurrentLayer === 'osm' }"
            @click="selectLayer('osm')"
          >
            <span
              class="text-sm"
              :class="
                mapCurrentLayer === 'osm' ? 'font-semibold text-black' : 'font-normal text-gray-700'
              "
              >{{ labels.openStreetMap }}</span
            >
          </button>
          <button
            type="button"
            class="w-full px-4 py-2 text-left rounded-none"
            :class="{ 'layer-menu-dropdown__item--active': mapCurrentLayer === 'satellite' }"
            @click="selectLayer('satellite')"
          >
            <span
              class="text-sm"
              :class="
                mapCurrentLayer === 'satellite'
                  ? 'font-semibold text-black'
                  : 'font-normal text-gray-700'
              "
              >{{ labels.satellite }}</span
            >
          </button>
        </div>
      </div>

      <!-- Map Controls (Small screens) -->
      <div
        v-if="isWeb && !isLarge"
        v-show="!isOptionsMenuOpen"
        class="absolute right-6 z-[1000] flex flex-col gap-2"
        style="bottom: calc(20px + 40px + 8px + 32px + 8px)"
      >
        <button
          type="button"
          class="w-8 h-8 bg-white rounded-full cursor-pointer flex items-center justify-center map-control-btn"
          :title="labels.locate"
          @click="handleLocate"
        >
          <q-icon name="my_location" size="18px" class="text-gray-700" />
        </button>

        <div class="w-8 flex flex-col rounded-full overflow-hidden map-control-zoom-container">
          <button
            type="button"
            class="w-full h-8 bg-white cursor-pointer flex items-center justify-center map-control-zoom-btn map-control-zoom-btn--top"
            :title="labels.zoomIn"
            @click="handleZoomIn"
          >
            <q-icon name="add" size="16px" class="text-gray-700" />
          </button>
          <button
            type="button"
            class="w-full h-8 bg-white cursor-pointer flex items-center justify-center map-control-zoom-btn"
            :title="labels.zoomOut"
            @click="handleZoomOut"
          >
            <q-icon name="remove" size="16px" class="text-gray-700" />
          </button>
        </div>
      </div>

      <!-- Layer Selector (Small screens) -->
      <div
        v-if="isWeb && !isLarge"
        v-show="!isOptionsMenuOpen"
        class="layer-menu-container absolute right-6 z-[1000]"
        style="bottom: calc(20px + 40px + 8px)"
      >
        <button
          type="button"
          class="w-8 h-8 bg-white rounded-full cursor-pointer flex items-center justify-center map-control-btn"
          :class="{ 'map-control-btn--active': isLayerMenuOpen }"
          @click="toggleLayerMenu"
        >
          <q-icon name="layers" size="18px" class="text-gray-700" />
        </button>

        <div
          v-show="isLayerMenuOpen"
          class="layer-menu-dropdown absolute bottom-10 right-0 bg-white py-0 min-w-[160px] z-[1001]"
        >
          <button
            type="button"
            class="w-full px-4 py-2 text-left rounded-none"
            :class="{ 'layer-menu-dropdown__item--active': mapCurrentLayer === 'locationiq' }"
            @click="selectLayer('locationiq')"
          >
            <span
              class="text-sm"
              :class="
                mapCurrentLayer === 'locationiq'
                  ? 'font-semibold text-black'
                  : 'font-normal text-gray-700'
              "
              >{{ labels.locationiqStreets }}</span
            >
          </button>
          <button
            type="button"
            class="w-full px-4 py-2 text-left rounded-none"
            :class="{ 'layer-menu-dropdown__item--active': mapCurrentLayer === 'cartodb' }"
            @click="selectLayer('cartodb')"
          >
            <span
              class="text-sm"
              :class="
                mapCurrentLayer === 'cartodb'
                  ? 'font-semibold text-black'
                  : 'font-normal text-gray-700'
              "
              >{{ labels.cartodbStreets }}</span
            >
          </button>
          <button
            type="button"
            class="w-full px-4 py-2 text-left rounded-none"
            :class="{ 'layer-menu-dropdown__item--active': mapCurrentLayer === 'osm' }"
            @click="selectLayer('osm')"
          >
            <span
              class="text-sm"
              :class="
                mapCurrentLayer === 'osm' ? 'font-semibold text-black' : 'font-normal text-gray-700'
              "
              >{{ labels.openStreetMap }}</span
            >
          </button>
          <button
            type="button"
            class="w-full px-4 py-2 text-left rounded-none"
            :class="{ 'layer-menu-dropdown__item--active': mapCurrentLayer === 'satellite' }"
            @click="selectLayer('satellite')"
          >
            <span
              class="text-sm"
              :class="
                mapCurrentLayer === 'satellite'
                  ? 'font-semibold text-black'
                  : 'font-normal text-gray-700'
              "
              >{{ labels.satellite }}</span
            >
          </button>
        </div>
      </div>

      <!-- Options Floating Button with Badges -->
      <div
        v-if="isWeb && hasAnyQuickActionPermission"
        class="options-menu-container absolute bottom-5 right-5 z-[1000] quick-actions-group"
      >
        <button
          v-show="!isOptionsMenuOpen"
          type="button"
          class="w-10 h-10 rounded-full cursor-pointer transition-all duration-300 flex items-center justify-center relative options-floating-btn"
          style="
            background-color: #000000;
            box-shadow:
              0 8px 25px -5px rgba(0, 0, 0, 0.1),
              0 8px 10px -5px rgba(0, 0, 0, 0.04);
          "
          @click="toggleOptionsMenu"
        >
          <q-icon name="add" size="24px" class="text-white options-floating-btn-icon" />
        </button>

        <div
          v-show="isOptionsMenuOpen"
          class="options-badges-container flex flex-col items-end gap-3"
        >
          <div
            v-if="canAccessComponent('main-get-in-touch-btn')"
            class="contact-supplier-wrapper group flex items-center gap-2 justify-end min-h-10 quick-action-get-in-touch"
          >
            <a
              href="#"
              role="button"
              class="contact-option-icon contact-option-icon-whatsapp h-10 w-0 min-w-0 overflow-hidden opacity-0 pointer-events-none rounded-full flex items-center justify-center flex-shrink-0 border-2 border-white shadow-lg transition-all duration-300 group-hover:w-10 group-hover:min-w-[40px] group-hover:opacity-100 group-hover:pointer-events-auto hover:scale-110"
              :title="labels.whatsapp"
              @click.prevent="handleWhatsApp"
            >
              <q-icon name="chat" size="22px" class="text-white" />
            </a>
            <a
              href="#"
              role="button"
              class="contact-option-icon contact-option-icon-email h-10 w-0 min-w-0 overflow-hidden opacity-0 pointer-events-none rounded-full flex items-center justify-center flex-shrink-0 border-2 border-white shadow-lg transition-all duration-300 group-hover:w-10 group-hover:min-w-[40px] group-hover:opacity-100 group-hover:pointer-events-auto hover:scale-110"
              :title="labels.email"
              @click.prevent="handleEmail"
            >
              <q-icon name="mail" size="22px" class="text-white" />
            </a>
            <button
              type="button"
              class="contact-supplier-btn w-auto min-w-[140px] h-10 rounded-full shadow-lg border-4 border-white cursor-pointer transition-all duration-300 hover:shadow-xl hover:scale-105 flex items-center justify-center gap-2 px-4"
              style="
                background-color: #ffeb3b;
                box-shadow:
                  0 8px 25px -5px rgba(0, 0, 0, 0.1),
                  0 8px 10px -5px rgba(0, 0, 0, 0.04);
              "
            >
              <q-icon name="contact_phone" size="20px" class="text-gray-800" />
              <span class="text-sm font-normal text-gray-800">{{ labels.getInTouch }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <AccountModal v-model="showAccountModal" />
  </div>
</template>

<style scoped lang="scss">
@import '@/css/main-page.scss';

/* Explicit dimensions — do not rely solely on Tailwind utilities for map sizing */
.main-page {
  height: 100vh;
  width: 100vw;
}

.main-page-shell {
  position: absolute;
  inset: 0;
}

.main-page-map {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.main-page-logo-wrap {
  left: 1.5rem;
  bottom: 1.25rem;
}

.tenant-logo-display-slot {
  width: 228px;
  max-width: 100%;
  height: 80px;
  margin-bottom: 0;
}

/* Map controls — match temp MainPage (border #dadce0, light hover) */
.map-control-btn {
  background-color: #ffffff !important;
  border: 1px solid #dadce0 !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
  transition: all 0.2s ease;
}

.map-control-btn:hover {
  background-color: #f8f9fa !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08) !important;
}

.map-control-btn:active {
  transform: scale(0.98);
}

.map-control-btn--active {
  background-color: #f8f9fa !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08) !important;
}

.map-control-zoom-container {
  background-color: #ffffff;
  border: 1px solid #dadce0 !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
  border-radius: 9999px;
  overflow: hidden;
  transition: all 0.2s ease;
}

.map-control-zoom-container:hover {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08) !important;
}

.map-control-zoom-btn {
  background-color: #ffffff !important;
  border: none;
  transition: all 0.2s ease;
}

.map-control-zoom-btn--top {
  border-bottom: 1px solid #dadce0 !important;
}

.map-control-zoom-btn:hover {
  background-color: #f8f9fa !important;
}

.map-control-zoom-btn:active {
  transform: scale(0.98);
}

.layer-menu-dropdown {
  border: 1px solid #dadce0 !important;
  box-shadow:
    0 2px 4px rgba(0, 0, 0, 0.08),
    0 1px 2px rgba(0, 0, 0, 0.06) !important;
  border-radius: 8px;
  overflow: hidden;
}

.layer-menu-dropdown button {
  background: #ffffff;
  transition: background-color 0.15s ease;
}

.layer-menu-dropdown button:hover {
  background-color: #f8f9fa !important;
}

.layer-menu-dropdown__item--active {
  background-color: #f8f9fa !important;
}

@keyframes wave-expand {
  0% {
    transform: scale(1);
    opacity: 0.5;
    border-width: 2px;
  }
  30% {
    transform: scale(1.3);
    opacity: 0.4;
    border-width: 4px;
  }
  60% {
    transform: scale(1.8);
    opacity: 0.2;
    border-width: 6px;
  }
  90% {
    transform: scale(2.2);
    opacity: 0;
    border-width: 8px;
  }
  100% {
    transform: scale(2.2);
    opacity: 0;
    border-width: 8px;
  }
}
</style>

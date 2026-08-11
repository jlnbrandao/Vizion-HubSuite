import { ref } from 'vue'
import { usePlatform } from '@/composables/usePlatform'
import L from '@/composables/leafletSetup'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import 'leaflet.markercluster'

export interface MapPosition {
  lat: number
  lng: number
}

export interface MapMarker {
  id: string
  position: MapPosition
  title: string
  icon?: string
  color?: string
  onClick?: () => void
  isSelected?: boolean
}

export type MapLayerType = 'satellite' | 'cartodb' | 'osm' | 'locationiq'

export function useMaps() {
  const { isNative, isWeb } = usePlatform()

  const leafletMap = ref<L.Map | null>(null)
  const leafletMarkers = ref<Array<{ id: string; marker: L.Marker; data: MapMarker }>>([])
  const markerClusterGroup = ref<L.MarkerClusterGroup | L.FeatureGroup | null>(null)

  const mapElement = ref<HTMLElement | null>(null)
  const isMapReady = ref(false)
  const currentLayer = ref<MapLayerType>('cartodb')

  const satelliteLayer = ref<L.TileLayer | null>(null)
  const cartodbLayer = ref<L.TileLayer | null>(null)
  const osmLayer = ref<L.TileLayer | null>(null)
  const locationiqLayer = ref<L.TileLayer | null>(null)

  const initMap = async (
    elementId: string,
    center: MapPosition = { lat: -22.2308, lng: -45.9361 },
    zoom: number = 13
  ) => {
    mapElement.value = document.getElementById(elementId) as HTMLElement

    if (!mapElement.value) {
      throw new Error(`Map container #${elementId} not found`)
    }

    isMapReady.value = false
    initWebMap(center, zoom)

    // Leaflet needs a non-zero size; reflow after layout settles.
    requestAnimationFrame(() => {
      leafletMap.value?.invalidateSize()
    })
  }

  const initWebMap = (center: MapPosition, zoom: number) => {
    try {
      if (leafletMap.value) {
        if (markerClusterGroup.value) {
          markerClusterGroup.value.clearLayers()
          markerClusterGroup.value.remove()
          markerClusterGroup.value = null
        }
        leafletMap.value.remove()
        leafletMap.value = null
      }

      const el = mapElement.value
      if (!el) {
        throw new Error('Map container element missing')
      }

      // Force non-zero size before Leaflet measures the container
      el.style.position = 'absolute'
      el.style.inset = '0'
      el.style.width = '100%'
      el.style.height = '100%'
      el.style.zIndex = '0'
      el.style.background = '#e5e7eb'

      leafletMap.value = L.map(el, {
        zoomControl: false,
        preferCanvas: true,
        zoomAnimation: true,
        markerZoomAnimation: true,
        renderer: L.canvas({ padding: 0.5 }),
        attributionControl: false,
        zoomSnap: 0.25,
        zoomDelta: 0.5
      }).setView([center.lat, center.lng], zoom)

      satelliteLayer.value = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
          attribution: '© Esri',
          maxZoom: 18,
          minZoom: 1,
          updateWhenZooming: false,
          updateWhenIdle: true,
          keepBuffer: 2
        }
      )

      cartodbLayer.value = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap contributors © CARTO',
        subdomains: 'abcd',
        maxZoom: 20,
        minZoom: 1,
        updateWhenZooming: false,
        updateWhenIdle: true,
        keepBuffer: 2
      })

      osmLayer.value = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
        minZoom: 1,
        updateWhenZooming: false,
        updateWhenIdle: true,
        keepBuffer: 2
      })

      locationiqLayer.value = L.tileLayer(
        'https://tiles.locationiq.com/v3/streets/r/{z}/{x}/{y}.png?key=pk.ff075d037d193a52b4da244159046024',
        {
          attribution: '© LocationIQ',
          maxZoom: 18,
          minZoom: 1,
          updateWhenZooming: false,
          updateWhenIdle: true,
          keepBuffer: 4,
          maxNativeZoom: 18,
          tileSize: 256,
          zoomOffset: 0,
          crossOrigin: true
        }
      )

      locationiqLayer.value.on('tileerror', (_event: L.TileErrorEvent) => {
        if (locationiqLayer.value && leafletMap.value) {
          setTimeout(() => {
            if (locationiqLayer.value && leafletMap.value) {
              leafletMap.value.invalidateSize()
              locationiqLayer.value.redraw()
            }
          }, 1500)
        }
      })

      locationiqLayer.value.on('loading', () => {})
      locationiqLayer.value.on('load', () => {})

      cartodbLayer.value.addTo(leafletMap.value as L.Map)

      if (typeof L.MarkerClusterGroup === 'function') {
        markerClusterGroup.value = new L.MarkerClusterGroup({
          chunkedLoading: false,
          spiderfyOnMaxZoom: true,
          showCoverageOnHover: false,
          zoomToBoundsOnClick: true,
          disableClusteringAtZoom: 18,
          maxClusterRadius: (zoomLevel: number) => {
            if (zoomLevel >= 18) return 40
            if (zoomLevel >= 15) return 50
            if (zoomLevel >= 12) return 60
            if (zoomLevel >= 10) return 70
            return 80
          },
          animate: true,
          singleMarkerMode: false,
          removeOutsideVisibleBounds: false,
          iconCreateFunction: (cluster: L.MarkerCluster) => {
            const count = cluster.getChildCount()
            let size = 'small'
            if (count > 100) {
              size = 'large'
            } else if (count > 10) {
              size = 'medium'
            }

            const dimension = size === 'large' ? 50 : size === 'medium' ? 40 : 35

            return L.divIcon({
              html: `<div style="
              background-color: #4a90e2;
              color: white;
              border-radius: 50%;
              width: ${dimension}px;
              height: ${dimension}px;
              display: flex;
              align-items: center;
              justify-content: center;
              font-weight: bold;
              font-size: ${size === 'large' ? '14px' : size === 'medium' ? '12px' : '11px'};
              border: 3px solid white;
              box-shadow: 0 2px 8px rgba(0,0,0,0.3);
              contain: layout style paint;
            ">${count}</div>`,
              className: 'marker-cluster-custom',
              iconSize: L.point(dimension, dimension),
            })
          },
        })
      } else {
        console.warn('[useMaps] MarkerClusterGroup unavailable — using FeatureGroup fallback')
        markerClusterGroup.value = L.featureGroup()
      }

      markerClusterGroup.value.addTo(leafletMap.value as L.Map)

      let syncTimeout: ReturnType<typeof setTimeout> | null = null
      let clusterRefreshScheduled = false

      const debouncedSync = () => {
        if (syncTimeout) {
          clearTimeout(syncTimeout)
        }
        syncTimeout = setTimeout(() => {
          leafletMap.value?.invalidateSize()
        }, 16)
      }

      const refreshClustersIfSupported = () => {
        const group = markerClusterGroup.value as L.MarkerClusterGroup | null
        if (group && typeof group.refreshClusters === 'function') {
          group.refreshClusters()
        }
      }

      const scheduleClusterRefresh = () => {
        if (clusterRefreshScheduled || !markerClusterGroup.value || !leafletMap.value) return
        clusterRefreshScheduled = true
        requestAnimationFrame(() => {
          clusterRefreshScheduled = false
          if (markerClusterGroup.value && leafletMap.value) {
            refreshClustersIfSupported()
            leafletMap.value.invalidateSize()
          }
        })
      }

      leafletMap.value.on('zoomanim', scheduleClusterRefresh)
      leafletMap.value.on('move', scheduleClusterRefresh)

      leafletMap.value.on('zoomend', () => {
        requestAnimationFrame(() => {
          if (markerClusterGroup.value && leafletMap.value) {
            refreshClustersIfSupported()
            leafletMap.value.invalidateSize()
          }
        })
        debouncedSync()
      })

      leafletMap.value.on('moveend', () => {
        scheduleClusterRefresh()
        debouncedSync()
      })

      leafletMap.value.on('resize', () => {
        leafletMap.value?.invalidateSize()
      })

      isMapReady.value = true
    } catch (error) {
      isMapReady.value = false
      throw error
    }
  }

  const getColoredIcon = (iconUrl: string, color: string): string => {
    const escapedUrl = iconUrl.replace(/'/g, "\\'")
    return `<div style="
      width: 16px;
      height: 16px;
      min-width: 16px;
      min-height: 16px;
      background-color: ${color};
      -webkit-mask-image: url('${escapedUrl}');
      -webkit-mask-repeat: no-repeat;
      -webkit-mask-position: center;
      -webkit-mask-size: contain;
      mask-image: url('${escapedUrl}');
      mask-repeat: no-repeat;
      mask-position: center;
      mask-size: contain;
      pointer-events: none;
      display: inline-block;
      vertical-align: middle;
    "></div>`
  }

  const createAddMarkerIcon = (
    marker: MapMarker,
    isSelected: boolean,
    hasAnySelected: boolean,
    markerInfo: MapMarker | null = null
  ) => {
    const currentMarker = markerInfo || marker
    const markerColor = currentMarker.color || '#28a745'
    const iconUrl = currentMarker.icon || '/src/assets/icons/default.svg'

    if (isSelected) {
      return L.divIcon({
        className: 'custom-marker-selected',
        html: `<div style="
          width: 30px;
          height: 30px;
          position: relative;
          z-index: 4;
        ">
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background-color: white;
            border: 2px solid ${currentMarker.color || '#28a745'};
            opacity: 0.5;
            animation: wave-expand 2s ease-out infinite;
            animation-delay: 0s;
          "></div>
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background-color: white;
            border: 2px solid ${currentMarker.color || '#28a745'};
            opacity: 0.5;
            animation: wave-expand 2s ease-out infinite;
            animation-delay: 0.7s;
          "></div>
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background-color: white;
            border: 2px solid ${currentMarker.color || '#28a745'};
            opacity: 0.5;
            animation: wave-expand 2s ease-out infinite;
            animation-delay: 1.4s;
          "></div>
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background-color: white;
            border: 2px solid ${currentMarker.color || '#28a745'};
            z-index: 5;
            opacity: 1.0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            justify-content: center;
          ">
            ${getColoredIcon(iconUrl, markerColor)}
          </div>
        </div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
        popupAnchor: [0, -15]
      })
    }

    return L.divIcon({
      className: 'custom-marker',
      html: `<div class="relative flex items-center justify-center rounded-full border-2 shadow-md" style="
        width: 30px;
        height: 30px;
        background-color: white;
        border-color: ${currentMarker.color || '#28a745'};
        opacity: ${hasAnySelected ? '0.5' : '1.0'};
        transform-origin: center center;
        transition: none;
        backface-visibility: hidden;
        transform-style: preserve-3d;
        will-change: transform;
      ">
        ${getColoredIcon(iconUrl, markerColor)}
      </div>`,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      popupAnchor: [0, -15]
    })
  }

  const createSelectionMarkerIcon = (
    markerData: MapMarker,
    selected: boolean,
    hasAnySelected: boolean,
    markerInfo: MapMarker | null = null
  ) => {
    const currentMarker = markerInfo || markerData
    const markerColor = currentMarker.color || '#28a745'
    const iconUrl = currentMarker.icon || '/src/assets/icons/default.svg'

    if (selected) {
      return L.divIcon({
        className: 'custom-marker-selected',
        html: `<div style="
          width: 20px;
          height: 20px;
          position: relative;
          z-index: 4;
        ">
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: ${currentMarker.color || '#28a745'};
            border: 2px solid white;
            opacity: 0.5;
            animation: wave-expand 2s ease-out infinite;
            animation-delay: 0s;
          "></div>
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: ${currentMarker.color || '#28a745'};
            border: 2px solid white;
            opacity: 0.5;
            animation: wave-expand 2s ease-out infinite;
            animation-delay: 0.7s;
          "></div>
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: ${currentMarker.color || '#28a745'};
            border: 2px solid white;
            opacity: 0.5;
            animation: wave-expand 2s ease-out infinite;
            animation-delay: 1.4s;
          "></div>
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: ${currentMarker.color || '#28a745'};
            border: 2px solid white;
            z-index: 5;
            opacity: 1.0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
          "></div>
        </div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
        popupAnchor: [0, -10]
      })
    }

    return L.divIcon({
      className: 'custom-marker',
      html: `<div class="relative flex items-center justify-center rounded-full border-2 shadow-md" style="
        width: 30px;
        height: 30px;
        background-color: white;
        border-color: ${currentMarker.color || '#28a745'};
        opacity: ${hasAnySelected ? '0.5' : '1.0'};
        transform-origin: center center;
        transition: none;
        backface-visibility: hidden;
        transform-style: preserve-3d;
        will-change: transform;
      ">
        ${getColoredIcon(iconUrl, markerColor)}
      </div>`,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      popupAnchor: [0, -15]
    })
  }

  const addMarker = async (marker: MapMarker) => {
    if (!isMapReady.value || !leafletMap.value || !markerClusterGroup.value) {
      return
    }

    const existingMarker = leafletMarkers.value.find(m => m.id === marker.id)
    if (existingMarker) {
      if (!markerClusterGroup.value.hasLayer(existingMarker.marker as unknown as L.Layer)) {
        markerClusterGroup.value.addLayer(existingMarker.marker as unknown as L.Layer)
      }
      return
    }

    try {
      const leafletMarker = L.marker([marker.position.lat, marker.position.lng], {
        icon: createAddMarkerIcon(
          marker,
          marker.isSelected || false,
          leafletMarkers.value.some(m => m.data.isSelected)
        ),
        riseOnHover: false,
        riseOffset: 0,
        keyboard: false,
        title: marker.title
      })

      if (!marker.isSelected) {
        leafletMarker.bindTooltip(marker.title, {
          permanent: false,
          direction: 'top',
          offset: [0, -10],
          className: 'device-tooltip'
        })
      }

      if (marker.onClick) {
        leafletMarker.on('click', () => {
          leafletMarker.closeTooltip()
          marker.onClick?.()
        })
      }

      markerClusterGroup.value.addLayer(leafletMarker as unknown as L.Layer)

      leafletMarkers.value.push({
        id: marker.id,
        marker: leafletMarker,
        data: marker
      })
    } catch (_error) {
      // Silently ignored
    }
  }

  const updateMarkerPosition = async (markerId: string, newPosition: MapPosition) => {
    const markerData = leafletMarkers.value.find(m => m.id === markerId)
    if (markerData) {
      markerData.marker.setLatLng([newPosition.lat, newPosition.lng])
    }
  }

  const updateMarkerSelection = (markerId: string, isSelected: boolean) => {
    const markerData = leafletMarkers.value.find(m => m.id === markerId)
    if (!markerData || !leafletMap.value) {
      return
    }

    markerData.data.isSelected = isSelected

    const hasAnySelected = leafletMarkers.value.some(m => m.data.isSelected)
    markerData.marker.setIcon(createSelectionMarkerIcon(markerData.data, isSelected, hasAnySelected))

    leafletMarkers.value.forEach(m => {
      if (m.id !== markerId) {
        m.marker.setIcon(
          createSelectionMarkerIcon(m.data, m.data.isSelected || false, hasAnySelected, m.data)
        )
      }
    })

    if (isSelected) {
      markerData.marker.unbindTooltip()
    } else {
      markerData.marker.bindTooltip(markerData.data.title, {
        permanent: false,
        direction: 'top',
        offset: [0, -10],
        className: 'device-tooltip'
      })
    }
  }

  const removeMarker = (markerId: string) => {
    const markerIndex = leafletMarkers.value.findIndex(m => m.id === markerId)
    if (markerIndex !== -1 && markerClusterGroup.value) {
      const markerEntry = leafletMarkers.value[markerIndex]
      if (markerEntry) {
        markerClusterGroup.value.removeLayer(markerEntry.marker as unknown as L.Layer)
        leafletMarkers.value.splice(markerIndex, 1)
      }
    }
  }

  const setMarkerVisibility = (markerId: string, visible: boolean) => {
    const markerData = leafletMarkers.value.find(m => m.id === markerId)
    if (!markerData || !markerClusterGroup.value) {
      return
    }

    if (visible) {
      if (!markerClusterGroup.value.hasLayer(markerData.marker as unknown as L.Layer)) {
        markerClusterGroup.value.addLayer(markerData.marker as unknown as L.Layer)
      }
    } else if (markerClusterGroup.value.hasLayer(markerData.marker as unknown as L.Layer)) {
      markerClusterGroup.value.removeLayer(markerData.marker as unknown as L.Layer)
    }
  }

  const clearAllMarkers = () => {
    markerClusterGroup.value?.clearLayers()
    leafletMarkers.value = []
  }

  const setView = async (center: MapPosition, zoom: number) => {
    leafletMap.value?.setView([center.lat, center.lng], zoom)
  }

  const fitBounds = () => {
    if (leafletMap.value && markerClusterGroup.value && leafletMarkers.value.length > 0) {
      const bounds = markerClusterGroup.value.getBounds()
      if (bounds.isValid()) {
        leafletMap.value.fitBounds(bounds.pad(0.1))
      }
    }
  }

  const removeAllLayers = () => {
    if (!leafletMap.value) return

    if (satelliteLayer.value && leafletMap.value.hasLayer(satelliteLayer.value as unknown as L.Layer)) {
      leafletMap.value.removeLayer(satelliteLayer.value as unknown as L.Layer)
    }
    if (cartodbLayer.value && leafletMap.value.hasLayer(cartodbLayer.value as unknown as L.Layer)) {
      leafletMap.value.removeLayer(cartodbLayer.value as unknown as L.Layer)
    }
    if (osmLayer.value && leafletMap.value.hasLayer(osmLayer.value as unknown as L.Layer)) {
      leafletMap.value.removeLayer(osmLayer.value as unknown as L.Layer)
    }
    if (locationiqLayer.value && leafletMap.value.hasLayer(locationiqLayer.value as unknown as L.Layer)) {
      leafletMap.value.removeLayer(locationiqLayer.value as unknown as L.Layer)
    }
  }

  const getLayerObject = (layerType: MapLayerType): L.TileLayer | null => {
    switch (layerType) {
      case 'satellite':
        return satelliteLayer.value as L.TileLayer
      case 'cartodb':
        return cartodbLayer.value as L.TileLayer
      case 'osm':
        return osmLayer.value as L.TileLayer
      case 'locationiq':
        return locationiqLayer.value as L.TileLayer
      default:
        return null
    }
  }

  const changeLayer = (layerType: MapLayerType) => {
    if (!leafletMap.value || currentLayer.value === layerType) {
      return
    }

    const currentView = leafletMap.value.getCenter()
    const currentZoom = leafletMap.value.getZoom()
    const newLayer = getLayerObject(layerType)

    if (!newLayer) {
      return
    }

    removeAllLayers()
    newLayer.addTo(leafletMap.value as L.Map)
    currentLayer.value = layerType
    newLayer.bringToFront()
    leafletMap.value.setView(currentView, currentZoom, { animate: false })
    leafletMap.value.invalidateSize()
  }

  const forceMarkerSync = () => {
    if (!leafletMap.value) return

    leafletMap.value.invalidateSize()
    const group = markerClusterGroup.value as L.MarkerClusterGroup | null
    if (group && typeof group.refreshClusters === 'function') {
      group.refreshClusters()
    }
  }

  const destroy = () => {
    if (markerClusterGroup.value) {
      markerClusterGroup.value.clearLayers()
      markerClusterGroup.value.remove()
      markerClusterGroup.value = null
    }

    if (leafletMap.value) {
      leafletMap.value.remove()
      leafletMap.value = null
    }

    leafletMarkers.value = []
    isMapReady.value = false
  }

  const updateMarkerTitle = (markerId: string, newTitle: string, onClickHandler?: () => void) => {
    const markerData = leafletMarkers.value.find(m => m.id === markerId)
    if (!markerData || !leafletMap.value) {
      return
    }

    markerData.data.title = newTitle

    if (onClickHandler) {
      markerData.data.onClick = onClickHandler
    }

    if (!markerData.data.isSelected) {
      markerData.marker.unbindTooltip()
      markerData.marker.bindTooltip(newTitle, {
        permanent: false,
        direction: 'top',
        offset: [0, -10],
        className: 'device-tooltip'
      })
    }

    const group = markerClusterGroup.value as L.MarkerClusterGroup | null
    if (group && typeof group.refreshClusters === 'function') {
      group.refreshClusters()
    }
  }

  return {
    isMapReady,
    isNative,
    isWeb,
    currentLayer,
    leafletMap,
    initMap,
    addMarker,
    updateMarkerPosition,
    updateMarkerSelection,
    updateMarkerTitle,
    removeMarker,
    setMarkerVisibility,
    clearAllMarkers,
    setView,
    fitBounds,
    changeLayer,
    forceMarkerSync,
    destroy
  }
}

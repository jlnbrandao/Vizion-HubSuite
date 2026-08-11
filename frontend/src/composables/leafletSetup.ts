/**
 * Ensures global `L` exists before leaflet.markercluster evaluates.
 * Import this module before `leaflet.markercluster`.
 */
import L from 'leaflet'

if (typeof window !== 'undefined') {
  ;(window as unknown as { L: typeof L }).L = L
}

export default L

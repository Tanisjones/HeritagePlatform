<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { HeritageRoute, RouteStop } from '@/types/heritage'

const props = defineProps<{
  route: HeritageRoute
}>()

const mapEl = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let markersLayer: L.LayerGroup | null = null
let lineLayer: L.Polyline | null = null

function stopLatLng(stop: RouteStop): [number, number] | null {
  const coords = stop.heritage_item?.location?.coordinates
  if (!coords || coords.length !== 2) return null
  const [lng, lat] = coords
  if (typeof lat !== 'number' || typeof lng !== 'number') return null
  return [lat, lng]
}

function createNumberedIcon(n: number) {
  return L.divIcon({
    className: 'route-stop-marker',
    html: `<div class="route-stop-marker__inner">${n}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -28],
  })
}

function parseWktLineString(wkt: string): [number, number][] | null {
  // Supports: "SRID=4326;LINESTRING (lng lat, lng lat, ...)" or "LINESTRING(lng lat, ...)"
  const match = wkt.match(/LINESTRING\s*\(\s*([^)]+)\s*\)/i)
  if (!match) return null
  const raw = match[1] || ''
  if (!raw) return null
  const pairs = raw
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => p.split(/\s+/).filter(Boolean))
  const points: [number, number][] = []
  for (const [lngStr, latStr] of pairs) {
    const lng = Number(lngStr)
    const lat = Number(latStr)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue
    points.push([lat, lng])
  }
  return points.length ? points : null
}

function routeLineCoords(): [number, number][] {
  const path: any = props.route.path
  if (path) {
    if (typeof path === 'string') {
      const parsed = parseWktLineString(path)
      if (parsed) return parsed
    }
    if (typeof path === 'object' && Array.isArray(path.coordinates) && path.type === 'LineString') {
      const coords = (path.coordinates as any[]).map((c) => [c?.[1], c?.[0]] as [number, number])
      const filtered = coords.filter((c) => typeof c[0] === 'number' && typeof c[1] === 'number')
      if (filtered.length) return filtered
    }
  }

  const stops = (props.route.stops || []).slice().sort((a, b) => a.order - b.order)
  return stops.map(stopLatLng).filter(Boolean) as [number, number][]
}

function init() {
  if (!mapEl.value || map) return

  map = L.map(mapEl.value, { zoomControl: true })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map)

  markersLayer = L.layerGroup().addTo(map)
  render()
}

function render() {
  if (!map || !markersLayer) return

  markersLayer.clearLayers()
  if (lineLayer) {
    lineLayer.remove()
    lineLayer = null
  }

  const stops = (props.route.stops || []).slice().sort((a, b) => a.order - b.order)
  const markerLatLngs: L.LatLngExpression[] = []

  for (const stop of stops) {
    const latlng = stopLatLng(stop)
    if (!latlng) continue
    markerLatLngs.push(latlng)
    const icon = createNumberedIcon(stop.order)
    const popupHtml = `
      <div style="min-width: 220px;">
        <div style="font-weight: 600; margin-bottom: 4px;">Stop ${stop.order}</div>
        <div style="font-weight: 600; color: #111827; margin-bottom: 6px;">${stop.heritage_item.title}</div>
        ${stop.arrival_instructions ? `<div style="color:#4b5563; font-size: 13px;">${stop.arrival_instructions}</div>` : ''}
      </div>
    `
    L.marker(latlng, { icon }).bindPopup(popupHtml).addTo(markersLayer)
  }

  const line = routeLineCoords()
  if (line.length >= 2) {
    lineLayer = L.polyline(line, {
      color: '#c76b4a',
      weight: 4,
      opacity: 0.9,
    }).addTo(map)
  }

  const boundsSource = (lineLayer ? line : markerLatLngs) as any[]
  if (boundsSource.length) {
    const bounds = L.latLngBounds(boundsSource)
    map.fitBounds(bounds, { padding: [24, 24] })
  } else {
    map.setView([-1.6735, -78.6479], 13)
  }
}

watch(
  () => props.route,
  () => render(),
  { deep: true }
)

onMounted(init)

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
    markersLayer = null
    lineLayer = null
  }
})
</script>

<template>
  <div ref="mapEl" class="w-full h-full rounded-xl overflow-hidden border border-gray-200" />
</template>

<style scoped>
:deep(.route-stop-marker) {
  background: transparent;
  border: none;
}

:deep(.route-stop-marker__inner) {
  width: 30px;
  height: 30px;
  background: #c76b4a;
  color: white;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  border: 2px solid white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
}
</style>

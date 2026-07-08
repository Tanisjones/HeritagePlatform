<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { parseLineString } from '@/utils/geo'
import { useCityStore } from '@/stores/city'
import type { HeritageRoute, RouteStop } from '@/types/heritage'

const cityStore = useCityStore()

const props = defineProps<{
  route: HeritageRoute
  // Live user position as [lng, lat] (GeoJSON order), shown as a blue dot.
  livePosition?: [number, number] | null
}>()

const { t } = useI18n()
const mapEl = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let markersLayer: L.LayerGroup | null = null
let lineLayer: L.Polyline | null = null
let positionMarker: L.CircleMarker | null = null

function escapeHtml(s: string): string {
  const div = document.createElement('div')
  div.textContent = s ?? ''
  return div.innerHTML
}

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

function routeLineCoords(): [number, number][] {
  // parseLineString handles both the WKT string and GeoJSON LineString cases.
  const parsed = parseLineString(props.route.path as any)
  if (parsed) return parsed

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
    const stopLabel = escapeHtml(t('routesUi.stop.stopLabel', { order: stop.order }))
    const popupHtml = `
      <div style="min-width: 220px;">
        <div style="font-weight: 600; margin-bottom: 4px;">${stopLabel}</div>
        <div style="font-weight: 600; color: #111827; margin-bottom: 6px;">${escapeHtml(stop.heritage_item.title)}</div>
        ${stop.arrival_instructions ? `<div style="color:#4b5563; font-size: 13px;">${escapeHtml(stop.arrival_instructions)}</div>` : ''}
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
    map.setView(cityStore.mapCenter ?? [-1.6735, -78.6479], cityStore.mapZoom)
  }

  updatePositionMarker()
}

function updatePositionMarker() {
  if (!map) return
  const pos = props.livePosition
  if (!pos) {
    if (positionMarker) {
      positionMarker.remove()
      positionMarker = null
    }
    return
  }
  const latlng: [number, number] = [pos[1], pos[0]] // [lat, lng]
  if (positionMarker) {
    positionMarker.setLatLng(latlng)
  } else {
    positionMarker = L.circleMarker(latlng, {
      radius: 8,
      color: '#2563eb',
      fillColor: '#3b82f6',
      fillOpacity: 0.9,
      weight: 3,
    }).addTo(map)
  }
}

watch(
  () => props.route,
  () => render(),
  { deep: true }
)

watch(() => props.livePosition, () => updatePositionMarker())

onMounted(init)

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
    markersLayer = null
    lineLayer = null
    positionMarker = null
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

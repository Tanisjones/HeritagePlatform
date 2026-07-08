<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Point } from '@/types/heritage'
import { useCityStore } from '@/stores/city'

const cityStore = useCityStore()

/**
 * Interactive authoring map for the route builder (raw Leaflet, matching
 * RouteMap.vue). Shows each stop as a numbered marker in order with a preview
 * polyline connecting them; clicking a marker removes that stop. Stops are real
 * heritage items with fixed coordinates, so markers are not draggable.
 */
type BuilderStop = {
  heritage_item_id: string
  order: number
  location?: Point | null
  title?: string
}

const props = defineProps<{ stops: BuilderStop[] }>()
// Emit the stop's heritage_item_id (stable) rather than a render-time index,
// which would go stale if the list is reordered while a popup stays open.
const emit = defineEmits<{ remove: [heritageItemId: string] }>()

const { t } = useI18n()
const mapEl = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let markersLayer: L.LayerGroup | null = null
let lineLayer: L.Polyline | null = null

function stopLatLng(stop: BuilderStop): [number, number] | null {
  const coords = stop.location?.coordinates
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

  const ordered = props.stops.slice().sort((a, b) => a.order - b.order)
  const latLngs: [number, number][] = []

  ordered.forEach((stop) => {
    const latlng = stopLatLng(stop)
    if (!latlng) return
    latLngs.push(latlng)
    const marker = L.marker(latlng, { icon: createNumberedIcon(stop.order) })
    const removeLabel = t('routesUi.actions.remove')
    const html = document.createElement('div')
    html.style.minWidth = '160px'
    html.innerHTML = `<div style="font-weight:600;margin-bottom:6px;">${stop.order}. ${escapeHtml(stop.title || '')}</div>`
    const btn = document.createElement('button')
    btn.textContent = removeLabel
    btn.style.cssText = 'color:#dc2626;font-size:13px;cursor:pointer;background:none;border:none;padding:0;'
    // Remove by stable id so a reorder between render and click can't delete the
    // wrong stop.
    const heritageItemId = stop.heritage_item_id
    btn.addEventListener('click', () => emit('remove', heritageItemId))
    html.appendChild(btn)
    marker.bindPopup(html)
    marker.addTo(markersLayer!)
  })

  if (latLngs.length >= 2) {
    lineLayer = L.polyline(latLngs, { color: '#c76b4a', weight: 4, opacity: 0.9, dashArray: '6 6' }).addTo(map)
  }

  if (latLngs.length) {
    map.fitBounds(L.latLngBounds(latLngs), { padding: [24, 24] })
  } else {
    map.setView(cityStore.mapCenter ?? [-1.6735, -78.6479], cityStore.mapZoom)
  }
}

function escapeHtml(s: string): string {
  const div = document.createElement('div')
  div.textContent = s
  return div.innerHTML
}

watch(() => props.stops, () => render(), { deep: true })

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

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIconUrl from 'leaflet/dist/images/marker-icon.png'
import markerIcon2xUrl from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png'

/**
 * LocationPickerMap — a single-point map on raw Leaflet, replacing the three
 * @vue-leaflet single-marker maps (contribution wizard, resource editor,
 * heritage detail) so the app has ONE Leaflet stack. In `readonly` mode it just
 * displays the marker; otherwise clicking the map moves the marker and emits the
 * new coordinates as `update:latlng` ([lat, lng]).
 */
const props = withDefaults(
  defineProps<{
    /** Marker position in Leaflet order [lat, lng]. */
    latlng: [number, number]
    zoom?: number
    /** Display only — no click-to-set. */
    readonly?: boolean
  }>(),
  { zoom: 13, readonly: false },
)

const emit = defineEmits<{ 'update:latlng': [value: [number, number]] }>()

// Fix Leaflet's default marker icon under bundlers (the classic broken-image bug).
const DefaultIcon = L.icon({
  iconUrl: markerIconUrl,
  iconRetinaUrl: markerIcon2xUrl,
  shadowUrl: markerShadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const mapEl = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let marker: L.Marker | null = null

function init() {
  if (!mapEl.value || map) return
  map = L.map(mapEl.value, { zoomControl: true }).setView(props.latlng, props.zoom)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map)
  marker = L.marker(props.latlng, { icon: DefaultIcon }).addTo(map)

  if (!props.readonly) {
    map.on('click', (e: L.LeafletMouseEvent) => {
      const next: [number, number] = [e.latlng.lat, e.latlng.lng]
      marker?.setLatLng(next)
      emit('update:latlng', next)
    })
  }
}

// Keep the marker in sync when the parent changes the location out-of-band
// (e.g. an existing item loads, or AI fills the address) and recenter onto it.
// Clicks that came from this map already moved the marker, so panTo is a no-op
// jitter-wise; guard against feedback loops by only panning on a real change.
watch(
  () => props.latlng,
  (next) => {
    if (!map || !marker || !next) return
    marker.setLatLng(next)
    const current = map.getCenter()
    if (Math.abs(current.lat - next[0]) > 1e-6 || Math.abs(current.lng - next[1]) > 1e-6) {
      map.panTo(next)
    }
  },
)

onMounted(init)
onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
    marker = null
  }
})
</script>

<template>
  <div ref="mapEl" class="w-full h-full" />
</template>

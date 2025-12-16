<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface HeritageMarker {
  id: string
  title: string
  coordinates: [number, number]
  type?: string
  category?: string
  image?: string
}

const props = defineProps<{
  markers?: HeritageMarker[]
  center?: [number, number]
  zoom?: number
}>()

const emit = defineEmits<{
  markerClick: [marker: HeritageMarker]
}>()

const mapContainer = ref<HTMLElement | null>(null)
let map: L.Map | null = null
const markerLayer = ref<L.LayerGroup | null>(null)

// Default center on Riobamba, Ecuador
const defaultCenter: [number, number] = [-1.6735, -78.6479]
const defaultZoom = 13

// Custom icon for heritage markers
const createMarkerIcon = (type?: string) => {
  const color = type === 'Tangible' ? '#c76b4a' : '#2a9d8f'
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background-color: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      ">
        <div style="
          transform: rotate(45deg);
          display: flex;
          align-items: center;
          justify-center;
          height: 100%;
        ">
          <svg style="width: 16px; height: 16px; fill: white;" viewBox="0 0 24 24">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
          </svg>
        </div>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  })
}

const initMap = () => {
  if (!mapContainer.value || map) return

  const center = props.center || defaultCenter
  const zoom = props.zoom || defaultZoom

  // Initialize map
  map = L.map(mapContainer.value).setView(center, zoom)

  // Add OpenStreetMap tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map)

  // Initialize marker layer
  markerLayer.value = L.layerGroup().addTo(map)

  // Add markers if provided
  if (props.markers) {
    addMarkers(props.markers)
  }
}

const addMarkers = (markers: HeritageMarker[]) => {
  if (!map || !markerLayer.value) return

  // Clear existing markers
  markerLayer.value.clearLayers()

  // Add new markers
  markers.forEach((marker) => {
    const icon = createMarkerIcon(marker.type)
    const leafletMarker = L.marker(marker.coordinates, { icon })
      .bindPopup(`
        <div style="min-width: 200px;">
          ${marker.image ? `<img src="${marker.image}" alt="${marker.title}" style="width: 100%; height: 120px; object-fit: cover; border-radius: 4px; margin-bottom: 8px;" />` : ''}
          <h3 style="font-weight: 600; font-size: 16px; margin-bottom: 4px;">${marker.title}</h3>
          ${marker.category ? `<p style="color: #6b7280; font-size: 14px; margin-bottom: 4px;">${marker.category}</p>` : ''}
          <button
            onclick="window.viewHeritageItem('${marker.id}')"
            style="
              margin-top: 8px;
              padding: 6px 12px;
              background-color: #c76b4a;
              color: white;
              border: none;
              border-radius: 4px;
              cursor: pointer;
              font-size: 14px;
              width: 100%;
            "
          >
            View Details
          </button>
        </div>
      `)
      .on('click', () => {
        emit('markerClick', marker)
      })

    markerLayer.value?.addLayer(leafletMarker)
  })
}

// Watch for marker updates
watch(() => props.markers, (newMarkers) => {
  if (newMarkers) {
    addMarkers(newMarkers)
  }
}, { deep: true })

onMounted(() => {
  initMap()
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div ref="mapContainer" class="w-full h-full rounded-lg overflow-hidden shadow-lg" />
</template>

<style scoped>
:deep(.custom-marker) {
  background: transparent;
  border: none;
}

:deep(.leaflet-popup-content-wrapper) {
  border-radius: 8px;
  padding: 0;
}

:deep(.leaflet-popup-content) {
  margin: 0;
  padding: 12px;
}
</style>

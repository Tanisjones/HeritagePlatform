<script setup lang="ts">
/**
 * HomeView.vue
 * 
 * Landing page of the application.
 * Features:
 * - Hero section with search bar
 * - Key statistics dashboard (Items, Types, Routes)
 * - Map preview showing heritage item locations
 * - Feature highlights (Learn, Explore, Contribute)
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MapContainer from '../components/map/MapContainer.vue'
import AppCard from '../components/common/AppCard.vue'
import AppButton from '../components/common/AppButton.vue'
import { heritageService, routeService } from '../services/api'
import { useI18n } from 'vue-i18n'

interface HeritageMarker {
  id: string
  title: string
  coordinates: [number, number]
  type?: string
  category?: string
  image?: string
}

const { t } = useI18n()
const router = useRouter()
const markers = ref<HeritageMarker[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const stats = ref({
  total: 0,
  tangible: 0,
  intangible: 0,
  routes: 0,
})

const searchQuery = ref('')

const performSearch = () => {
  const query = searchQuery.value.trim() ? { search: searchQuery.value } : undefined
  router.push({ name: 'explore', query })
}

const normalizeType = (value: unknown) => String(value || '').trim().toLowerCase()

const loadRoutesCount = async () => {
  try {
    const response = await routeService.list({ page_size: 1 })
    const count = response.data?.count
    stats.value.routes = typeof count === 'number' ? count : 0
  } catch (err) {
    console.error('Error loading routes:', err)
    stats.value.routes = 0
  }
}

const loadHeritageItems = async () => {
  try {
    loading.value = true
    error.value = null

    const data: any = await heritageService.getHeritageGeoJSON()
    
    // Determine where the features array is
    // Handle both { type: "FeatureCollection", features: [...] } and nested { features: { features: ... } }
    const features = Array.isArray(data.features) ? data.features : (data.features?.features || [])

    // Convert GeoJSON to marker format
    markers.value = features.map((feature: any) => {
      let coordinates: [number, number] = [0, 0]

      if (feature.geometry && typeof feature.geometry === 'object' && feature.geometry.coordinates) {
        // Standard GeoJSON
        coordinates = [feature.geometry.coordinates[1], feature.geometry.coordinates[0]]
      } else if (typeof feature.geometry === 'string' && feature.geometry.includes('POINT')) {
        // WKT Format: SRID=4326;POINT (-78.6575 -1.6732)
        // Extract numbers inside parentheses
        const matches = feature.geometry.match(/POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)/)
        if (matches && matches.length >= 3) {
          const lon = parseFloat(matches[1])
          const lat = parseFloat(matches[2])
          coordinates = [lat, lon]
          console.log(`Parsed WKT: ${feature.geometry} -> [${lat}, ${lon}]`)
        } else {
             console.warn('Failed to match WKT:', feature.geometry)
        }
      } else {
          console.warn('Unknown geometry format:', feature.geometry)
      }

      return {
        id: feature.id,
        title: feature.properties?.title || feature.title || 'Unknown',
        coordinates: coordinates,
        type: feature.properties?.heritage_type || 'Unknown',
        category: feature.properties?.heritage_category || 'Unknown',
        image: feature.properties?.primary_image || undefined,
      }
    }).filter((m: any) => m.coordinates[0] !== 0) // Filter out failed parses

    // Calculate stats
    stats.value.total = markers.value.length
    stats.value.tangible = markers.value.filter((m) => normalizeType(m.type) === 'tangible').length
    stats.value.intangible = markers.value.filter((m) => normalizeType(m.type) === 'intangible').length
  } catch (err: any) {
    console.error('Error loading heritage items:', err)
    error.value = err.message || 'Failed to load heritage items'
  } finally {
    loading.value = false
  }
}

const handleMarkerClick = (marker: HeritageMarker) => {
  console.log('Marker clicked:', marker)
  // In future, navigate to detail page
  // router.push(`/heritage/${marker.id}`)
}

// Add global function for popup button clicks
;(window as any).viewHeritageItem = (id: string) => {
  console.log('View heritage item:', id)
  // In future, navigate to detail page
  // router.push(`/heritage/${id}`)
}

onMounted(() => {
  loadHeritageItems()
  loadRoutesCount()
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Hero Section -->
    <section class="relative py-16 md:py-24 overflow-hidden z-0">
      <!-- Background Image -->
      <div class="absolute inset-0 z-0">
        <div class="absolute inset-0 bg-cover bg-center transition-transform duration-1000 hover:scale-105" style="background-image: url('/img/main_hero.jpg')"></div>
        <div class="absolute inset-0 bg-gradient-to-r from-black/80 via-black/60 to-transparent"></div>
      </div>

      <div class="container mx-auto px-4 relative z-10 text-white">
        <div class="max-w-3xl">
          <h1 class="text-4xl md:text-5xl font-display font-bold mb-6 leading-tight">
            {{ t('home.hero.title') }}
          </h1>
          <p class="text-xl md:text-2xl text-gray-200 mb-8 leading-relaxed font-light">
            {{ t('home.hero.subtitle') }}
          </p>
          <div class="mt-8 flex rounded-md shadow-2xl">
            <div class="relative flex-1 min-w-0 focus-within:z-10">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg class="h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
                </svg>
              </div>
              <input v-model="searchQuery" @keyup.enter="performSearch" type="text" name="search" id="search" class="appearance-none bg-white text-gray-900 placeholder-gray-500 focus:ring-primary-500 focus:border-primary-500 block w-full h-14 rounded-none rounded-l-lg pl-10 text-lg border-0 ring-1 ring-inset ring-gray-300" :placeholder="t('home.search.placeholder')">
            </div>
            <button @click="performSearch" class="-ml-px relative inline-flex items-center px-8 py-2 border border-transparent text-lg font-bold rounded-r-lg text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors shadow-lg">
              {{ t('home.search.button') }}
            </button>
          </div>
          <div class="flex flex-wrap gap-4 mt-8">
            <AppButton size="lg" variant="primary" class="!px-8 !py-4 !text-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all" @click="router.push('/explore')">
              {{ t('home.cta.explore') }}
            </AppButton>
            <AppButton size="lg" variant="ghost" class="!bg-white/10 !text-white !border-white/20 hover:!bg-white/20 !px-8 !py-4 !text-lg backdrop-blur-sm" @click="router.push('/contribute')">
              {{ t('home.cta.contribute') }}
            </AppButton>
          </div>
        </div>
      </div>
    </section>

    <!-- Stats Section -->
    <section class="container mx-auto px-4 -mt-8 mb-8 relative z-10">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <AppCard>
          <div class="text-center">
            <div class="text-3xl font-bold text-primary-600 mb-1">{{ stats.total }}</div>
            <div class="text-gray-600">{{ t('home.stats.items') }}</div>
          </div>
        </AppCard>
        <AppCard>
          <div class="text-center">
            <div class="text-3xl font-bold text-primary-600 mb-1">{{ stats.tangible }}</div>
            <div class="text-gray-600">{{ t('home.stats.tangible') }}</div>
          </div>
        </AppCard>
        <AppCard>
          <div class="text-center">
            <div class="text-3xl font-bold text-secondary-600 mb-1">{{ stats.intangible }}</div>
            <div class="text-gray-600">{{ t('home.stats.intangible') }}</div>
          </div>
        </AppCard>
        <AppCard>
          <div class="text-center">
            <div class="text-3xl font-bold text-primary-600 mb-1">{{ stats.routes }}</div>
            <div class="text-gray-600">{{ t('home.stats.routes') }}</div>
          </div>
        </AppCard>
      </div>
    </section>

    <!-- Map Section -->
    <section class="container mx-auto px-4 mb-12">
      <AppCard padding="none">
        <div class="p-4 border-b border-gray-200">
          <h2 class="text-2xl font-display font-bold text-gray-800">
            {{ t('home.map.title') }}
          </h2>
          <p class="text-gray-600 mt-1">
            {{ t('home.map.subtitle') }}
          </p>
        </div>

        <div class="relative">
          <!-- Loading State -->
          <div
            v-if="loading"
            class="absolute inset-0 flex items-center justify-center bg-gray-100 z-10"
            style="height: 600px"
          >
            <div class="text-center">
              <svg
                class="animate-spin h-12 w-12 text-primary-600 mx-auto mb-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <p class="text-gray-600">{{ t('home.map.loading') }}</p>
            </div>
          </div>

          <!-- Error State -->
          <div
            v-else-if="error"
            class="flex items-center justify-center bg-red-50 p-8"
            style="height: 600px"
          >
            <div class="text-center">
              <p class="text-red-600 mb-4">{{ error || t('home.map.error') }}</p>
              <AppButton @click="loadHeritageItems">
                {{ t('home.map.tryAgain') }}
              </AppButton>
            </div>
          </div>

          <!-- Map -->
          <div v-else style="height: 600px">
            <MapContainer
              :markers="markers"
              :center="[-1.6735, -78.6479]"
              :zoom="13"
              @marker-click="handleMarkerClick"
            />
          </div>
        </div>
      </AppCard>
    </section>

    <!-- Features Section -->
    <section class="container mx-auto px-4 mb-12">
      <h2 class="text-3xl font-display font-bold text-center mb-8">
        {{ t('home.features.title') }}
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <AppCard hoverable class="cursor-pointer" @click="router.push('/learn')">
          <div class="text-center">
            <div class="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10.394 2.08a1 1 0 00-.788 0l-7 3a1 1 0 000 1.84L5.25 8.051a.999.999 0 01.356-.257l4-1.714a1 1 0 11.788 1.838L7.667 9.088l1.94.831a1 1 0 00.787 0l7-3a1 1 0 000-1.838l-7-3zM3.31 9.397L5 10.12v4.102a8.969 8.969 0 00-1.05-.174 1 1 0 01-.89-.89 11.115 11.115 0 01.25-3.762zM9.3 16.573A9.026 9.026 0 007 14.935v-3.957l1.818.78a3 3 0 002.364 0l5.508-2.361a11.026 11.026 0 01.25 3.762 1 1 0 01-.89.89 8.968 8.968 0 00-5.35 2.524 1 1 0 01-1.4 0zM6 18a1 1 0 001-1v-2.065a8.935 8.935 0 00-2-.712V17a1 1 0 001 1z"></path>
              </svg>
            </div>
            <h3 class="text-xl font-semibold mb-2">{{ t('home.features.learn.title') }}</h3>
            <p class="text-gray-600">
              {{ t('home.features.learn.desc') }}
            </p>
          </div>
        </AppCard>

        <AppCard hoverable class="cursor-pointer" @click="router.push('/explore')">
          <div class="text-center">
            <div class="w-16 h-16 bg-secondary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-secondary-600" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"></path>
              </svg>
            </div>
            <h3 class="text-xl font-semibold mb-2">{{ t('home.features.explore.title') }}</h3>
            <p class="text-gray-600">
              {{ t('home.features.explore.desc') }}
            </p>
          </div>
        </AppCard>

        <AppCard hoverable class="cursor-pointer" @click="router.push('/contribute')">
          <div class="text-center">
            <div class="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"></path>
              </svg>
            </div>
            <h3 class="text-xl font-semibold mb-2">{{ t('home.features.contribute.title') }}</h3>
            <p class="text-gray-600">
              {{ t('home.features.contribute.desc') }}
            </p>
          </div>
        </AppCard>
      </div>
    </section>

  </div>
</template>

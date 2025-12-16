<script setup lang="ts">
/**
 * ExploreView.vue
 * 
 * Main interface for browsing heritage resources.
 * Features:
 * - Search by text (debounced)
 * - Filter by heritage type, category, parish, and media type
 * - Offline support: allows users to download the current query results for offline viewing
 * - Responsive grid layout for results
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/services/api'
import type { HeritageCategory, HeritageItem, HeritageType, Parish } from '@/types/heritage'
import { useI18n } from 'vue-i18n'

const { t, te } = useI18n()
const route = useRoute()
const router = useRouter()

const items = ref<HeritageItem[]>([])
const loading = ref(false)

const types = ref<HeritageType[]>([])
const categories = ref<HeritageCategory[]>([])
const parishes = ref<Parish[]>([])

const search = ref(route.query.search?.toString() || '')
const selectedTypeSlug = ref<string>(route.query.type?.toString() || 'all')
const selectedCategoryId = ref<string>(route.query.category?.toString() || '')
const selectedParishId = ref<string>(route.query.parish?.toString() || '')
const selectedMedia = ref<string>(route.query.media?.toString() || '')
const selectedOrdering = ref<string>(route.query.sort?.toString() || '-created_at')

const OFFLINE_AREA_STORAGE_KEY = 'hp_offline_area'
const offlineDownloading = ref(false)
const offlineDownloadError = ref<string | null>(null)

let debounceTimeout: ReturnType<typeof setTimeout> | null = null

const selectedTypeId = computed(() => {
  if (selectedTypeSlug.value === 'all') return ''
  const match = types.value.find((t) => t.slug === selectedTypeSlug.value)
  return match ? String(match.id) : ''
})

const currentQuerySnapshot = computed(() => {
  const params: Record<string, any> = {}
  if (search.value.trim()) params.search = search.value.trim()
  if (selectedTypeId.value) params.heritage_type = selectedTypeId.value
  if (selectedCategoryId.value) params.heritage_category = selectedCategoryId.value
  if (selectedParishId.value) params.parish = selectedParishId.value
  if (selectedOrdering.value) params.ordering = selectedOrdering.value

  if (selectedMedia.value === 'images') params.has_images = true
  if (selectedMedia.value === 'audio') params.has_audio = true
  if (selectedMedia.value === 'video') params.has_video = true
  if (selectedMedia.value === 'documents') params.has_documents = true
  if (selectedMedia.value === 'text') params.text_only = true

  return params
})

const hasOfflineBundleForCurrentQuery = computed(() => {
  try {
    const raw = localStorage.getItem(OFFLINE_AREA_STORAGE_KEY)
    if (!raw) return false
    const parsed = JSON.parse(raw)
    return JSON.stringify(parsed?.query ?? {}) === JSON.stringify(currentQuerySnapshot.value)
  } catch {
    return false
  }
})

const fetchItems = async () => {
  try {
    loading.value = true
    const params: Record<string, any> = { ...currentQuerySnapshot.value }

    const response = await api.get('/heritage-items/', { params })
    items.value = response.data.results
  } catch (error) {
    console.error('Error fetching heritage items:', error)
  } finally {
    loading.value = false
  }
};

const downloadForOffline = async () => {
  offlineDownloadError.value = null
  if (typeof navigator !== 'undefined' && navigator && navigator.onLine === false) {
    offlineDownloadError.value = t('explore.offline.mustBeOnline')
    return
  }

  offlineDownloading.value = true
  try {
    const baseParams = { ...currentQuerySnapshot.value }
    const pageSize = 100
    const maxPages = 5

    let page = 1
    let totalItems = 0

    while (page <= maxPages) {
      const response = await api.get('/heritage-items/', { params: { ...baseParams, page, page_size: pageSize } })
      const data = response.data
      const results: HeritageItem[] = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : []

      for (const listItem of results) {
        totalItems += 1
        const detailRes = await api.get(`/heritage-items/${listItem.id}/`)
        const detail: HeritageItem = detailRes.data

        const urls: Array<string | undefined | null> = [
          detail.primary_image,
          ...(detail.images || []).map((m) => m.file),
          ...(detail.audio || []).map((m) => m.file),
          ...(detail.video || []).map((m) => m.file),
          ...(detail.documents || []).map((m) => m.file),
        ]

        // Best-effort warm media cache
        await Promise.all(
          urls
            .filter((u): u is string => typeof u === 'string' && u.length > 0)
            .map((u) => fetch(u).catch(() => null))
        )
      }

      if (!data?.next || results.length === 0) break
      page += 1
    }

    localStorage.setItem(
      OFFLINE_AREA_STORAGE_KEY,
      JSON.stringify({
        query: currentQuerySnapshot.value,
        downloadedAt: Date.now(),
        itemCount: totalItems,
      })
    )
  } catch (e) {
    console.error('Offline download failed:', e)
    offlineDownloadError.value = t('explore.offline.downloadError')
  } finally {
    offlineDownloading.value = false
  }
}

const fetchFilterOptions = async () => {
  try {
    const [typesRes, categoriesRes, parishesRes] = await Promise.all([
      api.get('/types/'),
      api.get('/categories/all/'),
      api.get('/parishes/'),
    ])
    types.value = typesRes.data?.results || typesRes.data || []
    categories.value = categoriesRes.data || []
    parishes.value = parishesRes.data?.results || parishesRes.data || []
  } catch (e) {
    console.error('Error loading filter options:', e)
  }
}

const syncQuery = () => {
  router.replace({
    query: {
      ...route.query,
      search: search.value.trim() || undefined,
      type: selectedTypeSlug.value !== 'all' ? selectedTypeSlug.value : undefined,
      category: selectedCategoryId.value || undefined,
      parish: selectedParishId.value || undefined,
      media: selectedMedia.value || undefined,
      sort: selectedOrdering.value !== '-created_at' ? selectedOrdering.value : undefined,
    },
  })
}

const onSearchInput = () => {
  if (debounceTimeout) clearTimeout(debounceTimeout)
  
  debounceTimeout = setTimeout(() => {
    syncQuery()
  }, 300)
};

const clearFilters = () => {
  selectedTypeSlug.value = 'all'
  selectedCategoryId.value = ''
  selectedParishId.value = ''
  selectedMedia.value = ''
  selectedOrdering.value = '-created_at'
  syncQuery()
}

onMounted(async () => {
  await fetchFilterOptions()
  await fetchItems()
})

watch(
  () => route.query,
  (q) => {
    const nextSearch = q.search?.toString() || ''
    const nextType = q.type?.toString() || 'all'
    const nextCategory = q.category?.toString() || ''
    const nextParish = q.parish?.toString() || ''
    const nextMedia = q.media?.toString() || ''
    const nextSort = q.sort?.toString() || '-created_at'

    search.value = nextSearch
    selectedTypeSlug.value = nextType
    selectedCategoryId.value = nextCategory
    selectedParishId.value = nextParish
    selectedMedia.value = nextMedia
    selectedOrdering.value = nextSort

    fetchItems()
  },
  { deep: true }
)

const getResourceType = (item: HeritageItem): string | null => {
  const educational = item.lom_metadata?.educational;
  if (!educational) return null;
  // Handle array or single object
  if (Array.isArray(educational)) {
     return educational[0]?.learning_resource_type ?? null;
  }
  return educational.learning_resource_type || null;
};
</script>

<template>
  <div class="p-5">
    <h1 class="text-2xl font-bold text-gray-900 mb-4">{{ t('explore.title') }}</h1>

    <div class="mb-5 space-y-3">
      <input
        type="text"
        v-model="search"
        :placeholder="t('explore.searchPlaceholder')"
        @input="onSearchInput"
        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
      >

      <div class="flex flex-wrap gap-2 items-center">
        <div class="flex rounded-lg border border-gray-300 overflow-hidden bg-white">
          <button
            class="px-3 py-1.5 text-sm"
            :class="selectedTypeSlug === 'all' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-gray-50'"
            @click="selectedTypeSlug = 'all'; syncQuery()"
          >
            {{ t('explore.filters.all') }}
          </button>
          <button
            class="px-3 py-1.5 text-sm"
            :class="selectedTypeSlug === 'tangible' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-gray-50'"
            @click="selectedTypeSlug = 'tangible'; syncQuery()"
          >
            {{ t('explore.filters.tangible') }}
          </button>
          <button
            class="px-3 py-1.5 text-sm"
            :class="selectedTypeSlug === 'intangible' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-gray-50'"
            @click="selectedTypeSlug = 'intangible'; syncQuery()"
          >
            {{ t('explore.filters.intangible') }}
          </button>
        </div>

        <select
          v-model="selectedCategoryId"
          @change="syncQuery()"
          class="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm"
        >
          <option value="">{{ t('explore.filters.category') }}</option>
          <option v-for="c in categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
        </select>

        <select
          v-model="selectedParishId"
          @change="syncQuery()"
          class="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm"
        >
          <option value="">{{ t('explore.filters.parish') }}</option>
          <option v-for="p in parishes" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
        </select>

        <select
          v-model="selectedMedia"
          @change="syncQuery()"
          class="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm"
        >
          <option value="">{{ t('explore.filters.media') }}</option>
          <option value="images">{{ t('explore.filters.mediaImages') }}</option>
          <option value="audio">{{ t('explore.filters.mediaAudio') }}</option>
          <option value="video">{{ t('explore.filters.mediaVideo') }}</option>
          <option value="documents">{{ t('explore.filters.mediaDocuments') }}</option>
          <option value="text">{{ t('explore.filters.mediaTextOnly') }}</option>
        </select>

        <select
          v-model="selectedOrdering"
          @change="syncQuery()"
          class="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm"
        >
          <option value="-created_at">{{ t('explore.filters.sortNewest') }}</option>
          <option value="-view_count">{{ t('explore.filters.sortMostViewed') }}</option>
          <option value="-favorite_count">{{ t('explore.filters.sortMostFavorited') }}</option>
        </select>

        <button
          class="px-3 py-2 text-sm text-gray-700 hover:text-gray-900"
          @click="clearFilters"
        >
          {{ t('explore.filters.clear') }}
        </button>

        <button
          class="px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
          :disabled="offlineDownloading"
          @click="downloadForOffline"
        >
          {{ offlineDownloading ? t('explore.offline.downloading') : t('explore.offline.download') }}
        </button>

        <span v-if="hasOfflineBundleForCurrentQuery" class="text-xs text-gray-600">
          {{ t('explore.offline.ready') }}
        </span>
      </div>

      <p v-if="offlineDownloadError" class="text-sm text-red-600">
        {{ offlineDownloadError }}
      </p>
    </div>

    <div v-if="loading" class="flex justify-center items-center py-12">
      <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      <div v-for="item in items" :key="item.id" class="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
        <router-link :to="{ name: 'heritage-detail', params: { id: item.id } }">
          <div
            v-if="item.primary_image || item.images.length > 0"
            class="w-full h-40 bg-cover bg-center rounded-t-lg"
            :style="{ backgroundImage: `url('${item.primary_image || item.images[0]?.file}')` }"
            :aria-label="item.title"
          ></div>
          <div v-else class="w-full h-40 bg-gray-200 flex items-center justify-center rounded-t-lg">
             <span class="text-gray-400 text-4xl">🏛️</span>
          </div>
          <div class="p-4">
            <h2 class="text-lg font-semibold text-gray-900 mb-2">{{ item.title }}</h2>
            <div class="flex flex-wrap gap-2 text-xs">
              <!-- Heritage Type -->
              <span class="px-2 py-1 rounded-full bg-blue-100 text-blue-800 font-medium">
                {{ item.heritage_type.name }}
              </span>
              <!-- Heritage Category -->
              <span class="px-2 py-1 rounded-full bg-green-100 text-green-800 font-medium">
                {{ item.heritage_category.name }}
              </span>
              <!-- Resource Type (if available) -->
              <span v-if="getResourceType(item)" class="px-2 py-1 rounded-full bg-purple-100 text-purple-800 font-medium capitalize">
                {{ te(`lom.resource_type.${getResourceType(item)}`) ? t(`lom.resource_type.${getResourceType(item)}`) : getResourceType(item)?.replace(/_/g, ' ') }}
              </span>
            </div>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

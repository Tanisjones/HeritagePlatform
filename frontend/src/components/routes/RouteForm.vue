<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api, { aiService } from '@/services/api'
import { useAIAvailability } from '@/services/aiAvailability'
import { useAiError } from '@/composables/useAiError'
import AppButton from '@/components/common/AppButton.vue'
import AppInput from '@/components/common/AppInput.vue'
import AppCard from '@/components/common/AppCard.vue'
import AiActionButton from '@/components/common/AiActionButton.vue'
import RouteBuilderMap from '@/components/routes/RouteBuilderMap.vue'
import type { HeritageItem, Point, RouteCreateData } from '@/types/heritage'

const { t } = useI18n()

type StopDraft = {
  id?: string
  heritage_item_id: string
  order: number
  arrival_instructions: string
  suggested_time: string
  // Client-only: used by the map preview + AI suggestion, stripped before submit.
  location?: Point | null
  title?: string
}

const props = defineProps<{
  initial?: Partial<RouteCreateData>
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [payload: RouteCreateData]
}>()

const AVAILABLE_LANGUAGES = ['es', 'en'] as const

const title = ref(props.initial?.title || '')
const description = ref(props.initial?.description || '')
const theme = ref(props.initial?.theme || '')
const difficulty = ref<RouteCreateData['difficulty']>(props.initial?.difficulty || 'medium')
const distanceKm = ref<string>(
  typeof props.initial?.distance === 'number' && Number.isFinite(props.initial.distance)
    ? String(props.initial.distance)
    : ''
)
const estimatedDuration = ref<string>(
  typeof props.initial?.estimated_duration === 'string' ? props.initial.estimated_duration : ''
)
const wheelchairAccessible = ref<boolean>(!!props.initial?.wheelchair_accessible)
const publicTransitAccessible = ref<boolean>(!!props.initial?.public_transit_accessible)
const accessibilityNotes = ref(props.initial?.accessibility_notes || '')
const bestSeason = ref<RouteCreateData['best_season']>(props.initial?.best_season || '')
const estimatedCost = ref<string>(
  props.initial?.estimated_cost != null ? String(props.initial.estimated_cost) : ''
)
const costNotes = ref(props.initial?.cost_notes || '')
const availableLanguages = ref<string[]>(Array.isArray(props.initial?.available_languages) ? [...props.initial!.available_languages!] : [])

const stops = ref<StopDraft[]>(
  (props.initial?.stops || []).map((s, i) => ({
    id: s.id,
    heritage_item_id: s.heritage_item_id,
    order: typeof s.order === 'number' ? s.order : i + 1,
    arrival_instructions: s.arrival_instructions || '',
    suggested_time: s.suggested_time ?? '',
    location: s.location ?? null,
    title: s.title,
  }))
)

const search = ref('')
const searchLoading = ref(false)
const searchResults = ref<HeritageItem[]>([])

// --- AI suggestion ---
const { isAvailable: aiAvailable, refresh: refreshAIAvailability } = useAIAvailability()
const { applyAIError } = useAiError()
const aiLoading = ref(false)
const aiError = ref('')

onMounted(() => {
  refreshAIAvailability()
})

const canSubmit = computed(() => title.value.trim().length > 0 && description.value.trim().length > 0)

async function runSearch() {
  if (!search.value.trim()) {
    searchResults.value = []
    return
  }
  searchLoading.value = true
  try {
    const res = await api.get('/heritage-items/', { params: { search: search.value.trim(), page_size: 10 } })
    searchResults.value = res.data?.results || []
  } finally {
    searchLoading.value = false
  }
}

function reindex() {
  stops.value = stops.value.map((s, i) => ({ ...s, order: i + 1 }))
}

function addStop(item: HeritageItem) {
  if (stops.value.some((s) => s.heritage_item_id === item.id)) return
  stops.value.push({
    heritage_item_id: item.id,
    order: stops.value.length + 1,
    arrival_instructions: '',
    suggested_time: '',
    location: item.location ?? null,
    title: item.title,
  })
}

function removeStop(index: number) {
  stops.value.splice(index, 1)
  reindex()
}

function removeStopById(heritageItemId: string) {
  const idx = stops.value.findIndex((s) => s.heritage_item_id === heritageItemId)
  if (idx >= 0) removeStop(idx)
}

// --- Drag-and-drop reorder (native HTML5) ---
const dragIndex = ref<number | null>(null)

function onDragStart(index: number) {
  dragIndex.value = index
}

function onDrop(index: number) {
  const from = dragIndex.value
  dragIndex.value = null
  if (from === null || from === index) return
  const [moved] = stops.value.splice(from, 1)
  if (!moved) return
  stops.value.splice(index, 0, moved)
  reindex()
}

// Keyboard / touch fallback (native DnD is mouse-only).
function move(index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= stops.value.length) return
  const [moved] = stops.value.splice(index, 1)
  if (!moved) return
  stops.value.splice(target, 0, moved)
  reindex()
}

function toggleLanguage(code: string) {
  const idx = availableLanguages.value.indexOf(code)
  if (idx >= 0) availableLanguages.value.splice(idx, 1)
  else availableLanguages.value.push(code)
}

async function suggestWithAI() {
  aiError.value = ''
  aiLoading.value = true
  try {
    const result = await aiService.routeMetadata({
      title: title.value.trim() || undefined,
      stops: stops.value.map((s) => ({ title: s.title })).filter((s) => s.title),
    })
    // Only fill fields the user left empty; never clobber their input.
    if (result.description && !description.value.trim()) description.value = result.description
    if (result.theme && !theme.value.trim()) theme.value = result.theme
    if (result.difficulty && ['easy', 'medium', 'hard'].includes(result.difficulty)) {
      difficulty.value = result.difficulty as RouteCreateData['difficulty']
    }
    if (result.estimated_duration && !estimatedDuration.value.trim()) {
      estimatedDuration.value = result.estimated_duration
    }
  } catch (err) {
    applyAIError(err, aiError)
  } finally {
    aiLoading.value = false
  }
}

function submit() {
  const parsedDistance = distanceKm.value.trim() ? Number(distanceKm.value) : null
  const payload: RouteCreateData = {
    title: title.value.trim(),
    description: description.value.trim(),
    theme: theme.value.trim() || undefined,
    difficulty: difficulty.value || 'medium',
    distance: Number.isFinite(parsedDistance as any) ? (parsedDistance as number) : undefined,
    estimated_duration: estimatedDuration.value.trim() || undefined,
    wheelchair_accessible: wheelchairAccessible.value,
    public_transit_accessible: publicTransitAccessible.value,
    accessibility_notes: accessibilityNotes.value.trim() || undefined,
    best_season: bestSeason.value || undefined,
    estimated_cost: estimatedCost.value.trim() ? estimatedCost.value.trim() : undefined,
    cost_notes: costNotes.value.trim() || undefined,
    available_languages: availableLanguages.value.length ? availableLanguages.value : undefined,
    stops: stops.value.length
      ? stops.value.map((s) => ({
          // keep id (identity for non-destructive update); drop client-only helpers
          ...(s.id ? { id: s.id } : {}),
          heritage_item_id: s.heritage_item_id,
          order: s.order,
          arrival_instructions: s.arrival_instructions?.trim() || '',
          suggested_time: s.suggested_time.trim() || undefined,
        }))
      : undefined,
  }
  emit('submit', payload)
}
</script>

<template>
  <div class="space-y-5">
    <AppCard padding="lg">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ t('routesUi.form.routeDetailsTitle') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AppInput v-model="title" :label="t('routesUi.form.titleLabel')" :placeholder="t('routesUi.form.titlePlaceholder')" />
        <AppInput v-model="theme" :label="t('routesUi.form.themeLabel')" :placeholder="t('routesUi.form.themePlaceholder')" />
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('routesUi.form.descriptionLabel') }}</label>
          <textarea
            v-model="description"
            rows="4"
            class="w-full border border-gray-300 rounded-lg p-3 text-sm"
            :placeholder="t('routesUi.form.descriptionPlaceholder')"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('routesUi.difficulty.label') }}</label>
          <select v-model="difficulty" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="easy">{{ t('routesUi.difficulty.easy') }}</option>
            <option value="medium">{{ t('routesUi.difficulty.medium') }}</option>
            <option value="hard">{{ t('routesUi.difficulty.hard') }}</option>
          </select>
        </div>
        <AppInput
          v-model="estimatedDuration"
          :label="t('routesUi.form.estimatedDurationLabel')"
          placeholder="01:30:00"
        />
        <AppInput v-model="distanceKm" :label="t('routesUi.form.distanceLabel')" placeholder="2.5" />
      </div>

      <!-- AI suggestion -->
      <div class="mt-4">
        <AiActionButton
          :label="t('routesUi.builder.suggestWithAI')"
          :loading-label="t('routesUi.builder.suggesting')"
          :loading="aiLoading"
          :available="aiAvailable"
          :error="aiError"
          @click="suggestWithAI"
        />
        <p class="text-xs text-gray-500 mt-1 text-right">{{ t('routesUi.builder.aiHint') }}</p>
      </div>
    </AppCard>

    <!-- Additional details (previously admin-only) -->
    <AppCard padding="lg">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ t('routesUi.builder.moreDetailsTitle') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('routesUi.bestSeason.label') }}</label>
          <select v-model="bestSeason" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">—</option>
            <option value="spring">{{ t('routesUi.bestSeason.spring') }}</option>
            <option value="summer">{{ t('routesUi.bestSeason.summer') }}</option>
            <option value="autumn">{{ t('routesUi.bestSeason.autumn') }}</option>
            <option value="winter">{{ t('routesUi.bestSeason.winter') }}</option>
            <option value="year_round">{{ t('routesUi.bestSeason.yearRound') }}</option>
          </select>
        </div>
        <AppInput v-model="estimatedCost" :label="t('routesUi.builder.estimatedCostLabel')" placeholder="0.00" />
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('routesUi.builder.costNotesLabel') }}</label>
          <textarea v-model="costNotes" rows="2" class="w-full border border-gray-300 rounded-lg p-3 text-sm" />
        </div>
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('routesUi.builder.accessibilityNotesLabel') }}</label>
          <textarea v-model="accessibilityNotes" rows="2" class="w-full border border-gray-300 rounded-lg p-3 text-sm" />
        </div>
        <label class="flex items-center gap-2 text-sm text-gray-700">
          <input v-model="wheelchairAccessible" type="checkbox" class="rounded border-gray-300" />
          {{ t('routesUi.filters.wheelchairAccessible') }}
        </label>
        <label class="flex items-center gap-2 text-sm text-gray-700">
          <input v-model="publicTransitAccessible" type="checkbox" class="rounded border-gray-300" />
          {{ t('routesUi.builder.publicTransitAccessible') }}
        </label>
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('routesUi.builder.availableLanguagesLabel') }}</label>
          <div class="flex gap-4">
            <label v-for="code in AVAILABLE_LANGUAGES" :key="code" class="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                class="rounded border-gray-300"
                :checked="availableLanguages.includes(code)"
                @change="toggleLanguage(code)"
              />
              {{ t(`routesUi.builder.language_${code}`) }}
            </label>
          </div>
        </div>
      </div>
    </AppCard>

    <AppCard padding="lg">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ t('routesUi.form.stopsTitle') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <AppInput v-model="search" :placeholder="t('routesUi.form.searchHeritageItemsPlaceholder')" @keyup.enter="runSearch" />
        <div class="md:col-span-2 flex gap-2">
          <AppButton variant="secondary" :loading="searchLoading" @click="runSearch">{{ t('routesUi.actions.search') }}</AppButton>
          <div class="text-sm text-gray-500 flex items-center" v-if="searchLoading">{{ t('routesUi.loading') }}</div>
        </div>
      </div>

      <div v-if="searchResults.length" class="mt-4 border border-gray-200 rounded-lg divide-y">
        <button
          v-for="item in searchResults"
          :key="item.id"
          type="button"
          class="w-full text-left p-3 hover:bg-gray-50 flex items-center justify-between gap-3"
          @click="addStop(item)"
        >
          <div>
            <div class="text-sm font-medium text-gray-900">{{ item.title }}</div>
            <div class="text-xs text-gray-500 line-clamp-1">{{ item.description }}</div>
          </div>
          <span class="text-xs text-primary-700">{{ t('routesUi.actions.add') }}</span>
        </button>
      </div>

      <!-- Authoring map preview -->
      <div v-if="stops.length" class="mt-5" style="height: 320px">
        <RouteBuilderMap :stops="stops" @remove="removeStopById" />
      </div>

      <div class="mt-5">
        <div v-if="stops.length === 0" class="text-sm text-gray-600">
          {{ t('routesUi.states.addAtLeastOneStop') }}
        </div>
        <ol v-else class="space-y-3">
          <li
            v-for="(s, idx) in stops"
            :key="s.heritage_item_id"
            class="border border-gray-200 rounded-xl p-4"
            :class="{ 'opacity-50': dragIndex === idx }"
            draggable="true"
            @dragstart="onDragStart(idx)"
            @dragover.prevent
            @drop.prevent="onDrop(idx)"
            @dragend="dragIndex = null"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center gap-2">
                <span class="cursor-move text-gray-400 select-none" :title="t('routesUi.builder.dragToReorder')">⣿</span>
                <span class="text-sm font-semibold text-gray-900">
                  {{ t('routesUi.stop.stopLabel', { order: s.order }) }}
                  <span v-if="s.title" class="font-normal text-gray-600">· {{ s.title }}</span>
                </span>
              </div>
              <div class="flex items-center gap-2">
                <button type="button" class="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                        :disabled="idx === 0" :title="t('routesUi.builder.moveUp')" @click="move(idx, -1)">▲</button>
                <button type="button" class="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                        :disabled="idx === stops.length - 1" :title="t('routesUi.builder.moveDown')" @click="move(idx, 1)">▼</button>
                <button type="button" class="text-sm text-red-600 hover:text-red-700" @click="removeStop(idx)">
                  {{ t('routesUi.actions.remove') }}
                </button>
              </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
              <AppInput v-model="s.suggested_time" :label="t('routesUi.stop.suggestedTimeLabel')" placeholder="00:20:00" />
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('routesUi.stop.arrivalInstructionsLabel') }}</label>
                <input
                  v-model="s.arrival_instructions"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  :placeholder="t('routesUi.stop.arrivalInstructionsPlaceholder')"
                />
              </div>
            </div>
          </li>
        </ol>
      </div>
    </AppCard>

    <div class="flex justify-end">
      <AppButton :disabled="!canSubmit" :loading="loading" @click="submit">{{ t('routesUi.actions.saveRoute') }}</AppButton>
    </div>
  </div>
</template>

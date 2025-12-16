<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/services/api'
import AppButton from '@/components/common/AppButton.vue'
import AppInput from '@/components/common/AppInput.vue'
import AppCard from '@/components/common/AppCard.vue'
import type { HeritageItem, RouteCreateData } from '@/types/heritage'

const { t } = useI18n()

type StopDraft = {
  heritage_item_id: string
  order: number
  arrival_instructions: string
  suggested_time: string
}

const props = defineProps<{
  initial?: Partial<RouteCreateData>
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [payload: RouteCreateData]
}>()

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

const stops = ref<StopDraft[]>(
  (props.initial?.stops || []).map((s, i) => ({
    heritage_item_id: s.heritage_item_id,
    order: typeof s.order === 'number' ? s.order : i + 1,
    arrival_instructions: s.arrival_instructions || '',
    suggested_time: s.suggested_time ?? '',
  }))
)

const search = ref('')
const searchLoading = ref(false)
const searchResults = ref<HeritageItem[]>([])

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

function addStop(item: HeritageItem) {
  if (stops.value.some((s) => s.heritage_item_id === item.id)) return
  stops.value.push({
    heritage_item_id: item.id,
    order: stops.value.length + 1,
    arrival_instructions: '',
    suggested_time: '',
  })
}

function removeStop(index: number) {
  stops.value.splice(index, 1)
  stops.value = stops.value.map((s, i) => ({ ...s, order: i + 1 }))
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
    stops: stops.value.length
      ? stops.value.map((s) => ({
          ...s,
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
        <label class="flex items-center gap-2 text-sm text-gray-700 md:col-span-2">
          <input v-model="wheelchairAccessible" type="checkbox" class="rounded border-gray-300" />
          {{ t('routesUi.filters.wheelchairAccessible') }}
        </label>
      </div>
    </AppCard>

    <AppCard padding="lg">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ t('routesUi.form.stopsTitle') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <AppInput v-model="search" :placeholder="t('routesUi.form.searchHeritageItemsPlaceholder')" />
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

      <div class="mt-5">
        <div v-if="stops.length === 0" class="text-sm text-gray-600">
          {{ t('routesUi.states.addAtLeastOneStop') }}
        </div>
        <ol v-else class="space-y-3">
          <li v-for="(s, idx) in stops" :key="s.heritage_item_id" class="border border-gray-200 rounded-xl p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="text-sm font-semibold text-gray-900">{{ t('routesUi.stop.stopLabel', { order: s.order }) }}</div>
              <button type="button" class="text-sm text-red-600 hover:text-red-700" @click="removeStop(idx)">
                {{ t('routesUi.actions.remove') }}
              </button>
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

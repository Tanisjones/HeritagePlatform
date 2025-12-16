<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppInput from '@/components/common/AppInput.vue'

const { t } = useI18n()

const props = defineProps<{
  initial?: Record<string, any>
}>()

const emit = defineEmits<{
  change: [params: Record<string, any>]
}>()

const search = ref((props.initial?.search as string) || '')
const difficulty = ref((props.initial?.difficulty as string) || '')
const bestSeason = ref((props.initial?.best_season as string) || '')
const wheelchair = ref(!!props.initial?.wheelchair_accessible)

const params = computed(() => {
  const p: Record<string, any> = {}
  if (search.value.trim()) p.search = search.value.trim()
  if (difficulty.value) p.difficulty = difficulty.value
  if (bestSeason.value) p.best_season = bestSeason.value
  if (wheelchair.value) p.wheelchair_accessible = true
  return p
})

watch(params, (p) => emit('change', p), { deep: true })
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-xl p-4">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
      <AppInput v-model="search" :placeholder="t('routesUi.filters.searchPlaceholder')" />
      <select v-model="difficulty" class="border border-gray-300 rounded-lg px-3 py-2 text-sm">
        <option value="">{{ t('routesUi.difficulty.label') }}</option>
        <option value="easy">{{ t('routesUi.difficulty.easy') }}</option>
        <option value="medium">{{ t('routesUi.difficulty.medium') }}</option>
        <option value="hard">{{ t('routesUi.difficulty.hard') }}</option>
      </select>
      <select v-model="bestSeason" class="border border-gray-300 rounded-lg px-3 py-2 text-sm">
        <option value="">{{ t('routesUi.bestSeason.label') }}</option>
        <option value="spring">{{ t('routesUi.bestSeason.spring') }}</option>
        <option value="summer">{{ t('routesUi.bestSeason.summer') }}</option>
        <option value="autumn">{{ t('routesUi.bestSeason.autumn') }}</option>
        <option value="winter">{{ t('routesUi.bestSeason.winter') }}</option>
        <option value="year_round">{{ t('routesUi.bestSeason.yearRound') }}</option>
      </select>
      <label class="flex items-center gap-2 text-sm text-gray-700">
        <input v-model="wheelchair" type="checkbox" class="rounded border-gray-300" />
        {{ t('routesUi.filters.wheelchairAccessible') }}
      </label>
    </div>
  </div>
</template>

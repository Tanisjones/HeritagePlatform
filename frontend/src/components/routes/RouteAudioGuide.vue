<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { RouteStop } from '@/types/heritage'

/**
 * Audioguide for a route walk. Shows a native audio player for the given stop's
 * first audio file (RouteStop.audio_url). In "guided walk" mode the parent points
 * this at the stop the user just checked in at, and we autoplay it so the guide
 * follows the walk. Hidden when the stop has no audio.
 */
const props = defineProps<{
  stop: RouteStop | null
  // When true, autoplay the audio whenever the stop changes (guided walk).
  autoplay?: boolean
}>()

const { t } = useI18n()
const audioEl = ref<HTMLAudioElement | null>(null)

const audioUrl = computed(() => props.stop?.audio_url || null)

// Autoplay on arrival at a new stop. Browsers may block autoplay without a prior
// user gesture; that's fine — the controls remain and the failure is swallowed.
watch(
  () => props.stop?.id,
  async () => {
    if (!props.autoplay || !audioUrl.value) return
    await nextTick()
    try {
      await audioEl.value?.play()
    } catch {
      /* autoplay blocked; user can press play */
    }
  },
)
</script>

<template>
  <section v-if="audioUrl" class="bg-white border border-gray-200 rounded-xl p-6">
    <div class="flex items-center gap-2 mb-3">
      <span aria-hidden="true">🎧</span>
      <h3 class="text-lg font-semibold text-gray-900">{{ t('routesUi.audio.title') }}</h3>
    </div>
    <p v-if="stop" class="text-sm text-gray-600 mb-2">
      {{ t('routesUi.audio.nowPlaying', { title: stop.heritage_item.title }) }}
    </p>
    <audio ref="audioEl" :key="audioUrl" controls preload="none" class="w-full">
      <source :src="audioUrl" />
    </audio>
  </section>
</template>

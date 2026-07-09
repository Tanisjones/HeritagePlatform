<script setup lang="ts">
/**
 * P.4 — bind ONE real content item to a lesson activity: a heritage item, a route,
 * an educational resource, or (A.5) a quiz — a learning object that carries
 * assessment questions. Searches the existing list endpoints (?search=),
 * debounced, and emits the chosen FK id (+ a display title for the card). Binding
 * is single-target: choosing one kind clears the others (matches how an activity
 * links a single primary resource).
 *
 * v-model is the activity object itself (the FK fields are mutated in place via
 * `update:binding` events the parent applies), but to stay decoupled this
 * component only READS the current binding via props and EMITS the change.
 */
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/services/api'
import { unwrapResults } from '@/utils/pagination'

type ContentKind = 'heritage_item' | 'route' | 'educational_resource' | 'lom_general'

const props = defineProps<{
  heritageItem?: string | null
  route?: string | null
  educationalResource?: number | null
  lomGeneral?: string | null
  heritageItemTitle?: string | null
  routeTitle?: string | null
  educationalResourceTitle?: string | null
  lomGeneralTitle?: string | null
}>()

const emit = defineEmits<{
  (
    e: 'change',
    payload: {
      heritage_item: string | null
      route: string | null
      educational_resource: number | null
      lom_general: string | null
      /** Display title of the picked row, so the chip is right before save. */
      picked_title?: string | null
    },
  ): void
}>()

const { t } = useI18n()

const KINDS: {
  key: ContentKind
  endpoint: string
  labelKey: string
  extraParams?: Record<string, unknown>
}[] = [
  { key: 'heritage_item', endpoint: '/heritage-items/', labelKey: 'lessonPlans.content.heritage' },
  { key: 'route', endpoint: '/routes/', labelKey: 'lessonPlans.content.route' },
  { key: 'educational_resource', endpoint: '/educational-resources/', labelKey: 'lessonPlans.content.resource' },
  // Learning objects that actually carry a quiz (server-filtered).
  { key: 'lom_general', endpoint: '/lom/', labelKey: 'lessonPlans.content.quiz', extraParams: { has_questions: 1 } },
]

const CHIP_LABEL_KEY: Record<ContentKind, string> = {
  heritage_item: 'lessonPlans.content.heritage',
  route: 'lessonPlans.content.route',
  educational_resource: 'lessonPlans.content.resource',
  lom_general: 'lessonPlans.content.quiz',
}

const activeKind = ref<ContentKind>('heritage_item')
const query = ref('')
const results = ref<{ id: string | number; title: string; meta?: string }[]>([])
const searching = ref(false)
const open = ref(false)

/** The currently-bound content, if any (for the summary chip). */
const currentBinding = computed<{ kind: ContentKind; title: string } | null>(() => {
  if (props.heritageItem) return { kind: 'heritage_item', title: props.heritageItemTitle || t('lessonPlans.content.linkedHeritage') }
  if (props.route) return { kind: 'route', title: props.routeTitle || t('lessonPlans.content.linkedRoute') }
  if (props.educationalResource != null)
    return { kind: 'educational_resource', title: props.educationalResourceTitle || t('lessonPlans.content.linkedResource') }
  if (props.lomGeneral) return { kind: 'lom_general', title: props.lomGeneralTitle || t('lessonPlans.content.linkedQuiz') }
  return null
})

let debounceTimer: ReturnType<typeof setTimeout> | null = null
watch(query, () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(runSearch, 300)
})

// Monotonic request token: only the most recently-issued search may write
// results, so a slow earlier response (or a kind switch mid-flight) can't clobber
// a newer one and bind the wrong FK kind.
let searchSeq = 0
async function runSearch() {
  const q = query.value.trim()
  // The quiz catalog is small — list it even without a search term so the tab
  // isn't an empty box; the other kinds still wait for a query.
  if (!q && activeKind.value !== 'lom_general') {
    results.value = []
    return
  }
  const kind = KINDS.find((k) => k.key === activeKind.value)!
  const seq = ++searchSeq
  searching.value = true
  try {
    const res = await api.get(kind.endpoint, {
      params: { ...(q ? { search: q } : {}), page_size: 8, ...(kind.extraParams || {}) },
    })
    if (seq !== searchSeq) return // a newer search superseded this one
    const rows = unwrapResults<any>(res.data)
    results.value = rows.slice(0, 8).map((r: any) => ({
      id: r.id,
      title: r.title || r.name || String(r.id),
      meta:
        kind.key === 'lom_general' && Array.isArray(r.questions)
          ? t('lessonPlans.content.questionCount', r.questions.length)
          : undefined,
    }))
  } catch {
    if (seq === searchSeq) results.value = []
  } finally {
    if (seq === searchSeq) searching.value = false
  }
}

function pick(row: { id: string | number; title: string }) {
  const payload = {
    heritage_item: null as string | null,
    route: null as string | null,
    educational_resource: null as number | null,
    lom_general: null as string | null,
    picked_title: row.title,
  }
  if (activeKind.value === 'heritage_item') payload.heritage_item = String(row.id)
  else if (activeKind.value === 'route') payload.route = String(row.id)
  else if (activeKind.value === 'educational_resource') payload.educational_resource = Number(row.id)
  else payload.lom_general = String(row.id)
  emit('change', payload)
  open.value = false
  query.value = ''
  results.value = []
}

function clearBinding() {
  emit('change', {
    heritage_item: null, route: null, educational_resource: null, lom_general: null, picked_title: null,
  })
}

function switchKind(kind: ContentKind) {
  activeKind.value = kind
  results.value = []
  if (query.value.trim() || kind === 'lom_general') runSearch()
}
</script>

<template>
  <div class="text-sm">
    <!-- current binding chip -->
    <div v-if="currentBinding" class="flex items-center gap-2 flex-wrap">
      <span class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-secondary-100 text-secondary-800">
        <span class="font-medium">{{ t(CHIP_LABEL_KEY[currentBinding.kind]) }}:</span>
        {{ currentBinding.title }}
      </span>
      <button type="button" class="text-xs text-red-600 hover:underline" @click="clearBinding">
        {{ t('lessonPlans.content.unlink') }}
      </button>
      <button type="button" class="text-xs text-primary-600 hover:underline" @click="open = !open">
        {{ t('lessonPlans.content.change') }}
      </button>
    </div>
    <button v-else type="button" class="text-primary-600 hover:underline" @click="open = !open">
      + {{ t('lessonPlans.content.link') }}
    </button>

    <!-- picker -->
    <div v-if="open" class="mt-2 border border-gray-200 rounded-lg p-3 bg-gray-50">
      <div class="inline-flex rounded-md border border-gray-300 overflow-hidden mb-2 text-xs">
        <button
          v-for="k in KINDS"
          :key="k.key"
          type="button"
          class="px-2.5 py-1"
          :class="activeKind === k.key ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 hover:bg-primary-50'"
          @click="switchKind(k.key)"
        >
          {{ t(k.labelKey) }}
        </button>
      </div>
      <input
        v-model="query"
        type="search"
        class="w-full px-3 py-1.5 border border-gray-300 rounded-lg"
        :placeholder="t('lessonPlans.content.searchPlaceholder')"
      />
      <div class="mt-2 max-h-48 overflow-y-auto">
        <div v-if="searching" class="text-gray-400 py-2 text-center text-xs">{{ t('common.loading') }}</div>
        <ul v-else-if="results.length" class="divide-y divide-gray-100">
          <li v-for="row in results" :key="String(row.id)">
            <button
              type="button"
              class="w-full text-left px-2 py-1.5 hover:bg-primary-50 rounded flex items-center justify-between gap-2"
              @click="pick(row)"
            >
              <span class="truncate">{{ row.title }}</span>
              <span v-if="row.meta" class="flex-shrink-0 text-xs text-gray-400">{{ row.meta }}</span>
            </button>
          </li>
        </ul>
        <div v-else-if="query.trim() || activeKind === 'lom_general'" class="text-gray-400 py-2 text-center text-xs">
          {{ activeKind === 'lom_general' ? t('lessonPlans.content.noQuizzes') : t('lessonPlans.content.noResults') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { aiService, curatorService } from '@/services/api'
import { useAIAvailability } from '@/services/aiAvailability'
import MapContainer from '@/components/map/MapContainer.vue'
import type {
  CuratorReviewDetail,
  QualityScore,
  ReviewChecklist,
  ReviewChecklistResponse,
} from '@/types/moderation'
import QualityScoreCard from '@/components/moderation/QualityScoreCard.vue'
import ReviewChecklistComponent from '@/components/moderation/ReviewChecklistComponent.vue'
import CuratorNotesEditor from '@/components/moderation/CuratorNotesEditor.vue'
import VersionHistoryTimeline from '@/components/moderation/VersionHistoryTimeline.vue'
import ReviewActions from '@/components/moderation/ReviewActions.vue'
import FlagContributionModal from '@/components/moderation/FlagContributionModal.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const parsedLocation = computed<[number, number] | null>(() => {
  const loc = (detail.value as any)?.heritage_item?.location
  if (!loc) return null
  
  // Handle GeoJSON object if it comes that way (from some serializers)
  if (typeof loc === 'object' && Array.isArray(loc.coordinates)) {
    // GeoJSON is [lng, lat], Leaflet wants [lat, lng]
    return [loc.coordinates[1], loc.coordinates[0]]
  }

  // Handle string "SRID=4326;POINT (-78.6479 -1.6735)" or "POINT (-78.6479 -1.6735)"
  // Extract content inside parens
  const match = loc.toString().match(/\(([^)]+)\)/)
  if (match && match[1]) {
    const parts = match[1].trim().split(/\s+/)
    if (parts.length >= 2) {
      const lng = parseFloat(parts[0])
      const lat = parseFloat(parts[1])
      if (!isNaN(lng) && !isNaN(lat)) {
         return [lat, lng]
      }
    }
  }
  return null
})

const loading = ref(false)
const error = ref<string | null>(null)
const detail = ref<CuratorReviewDetail | null>(null)

const score = ref<QualityScore>({
  completeness_score: 0,
  accuracy_score: 0,
  media_quality_score: 0,
  notes: '',
})
const checklist = ref<ReviewChecklist | null>(null)
const checklistResponses = ref<ReviewChecklistResponse[]>([])

const flagModalOpen = ref(false)

type AIReview = {
  missing_fields: string[]
  risk_flags: string[]
  curator_feedback_draft: string
  suggested_edits?: Record<string, string>
}

const aiLoading = ref(false)
const aiError = ref<string | null>(null)
const aiReview = ref<AIReview | null>(null)
const canCopy = typeof globalThis !== 'undefined' && Boolean((globalThis as any).navigator?.clipboard)
const { isAvailable: aiAvailable, refresh: refreshAIAvailability, markUnavailable: markAIUnavailable } =
  useAIAvailability()

function getCurrentLocale() {
  return localStorage.getItem('hp_locale') || 'es'
}

async function copyAIFeedback() {
  const text = aiReview.value?.curator_feedback_draft || ''
  const clipboard = (globalThis as any).navigator?.clipboard
  if (!clipboard || typeof clipboard.writeText !== 'function') return
  await clipboard.writeText(text)
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await curatorService.getQueueItem(id.value)
    detail.value = res.data

    if (detail.value?.quality_score) score.value = detail.value.quality_score
    checklistResponses.value = detail.value?.checklist_responses ?? []

    const checklistRes = await curatorService.checklist(id.value)
    checklist.value = checklistRes.data || null
    if (checklist.value && checklistResponses.value.length === 0) {
      checklistResponses.value = checklist.value.items.map((i) => ({
        heritage_item: id.value,
        checklist_item: i.id,
        is_checked: false,
        notes: '',
      }))
    }
  } catch (e: any) {
    error.value = e?.message ?? t('curatorReview.failedToLoad')
  } finally {
    loading.value = false
  }
}

async function runAIReview() {
  if (aiLoading.value) return
  if (!detail.value) return
  aiError.value = null
  try {
    aiLoading.value = true
    const res = await aiService.curatorReview({
      language: getCurrentLocale(),
      item: (detail.value as any).heritage_item ?? detail.value,
    })
    aiReview.value = res

    if (typeof res.curator_feedback_draft === 'string' && res.curator_feedback_draft.trim()) {
      const prefix = score.value.notes ? `${score.value.notes}\n\n` : ''
      score.value.notes = `${prefix}${res.curator_feedback_draft}`.trim()
    }
  } catch (e: any) {
    const status = e?.response?.status
    if (status === 503) {
      aiError.value = t('curatorReview.aiReview.unavailable')
      markAIUnavailable()
    }
    else if (status === 429) aiError.value = t('curatorReview.aiReview.tooManyRequests')
    else aiError.value = e?.message ?? t('curatorReview.aiReview.requestFailed')
  } finally {
    aiLoading.value = false
  }
}

async function saveScore() {
  await curatorService.setScore(id.value, score.value)
  await load()
}

async function saveChecklist() {
  await curatorService.submitChecklistResponses(id.value, checklistResponses.value)
  await load()
}

async function addNote(payload: { content: string; is_pinned: boolean }) {
  await curatorService.addNote(id.value, payload)
  await load()
}

async function flagContribution(payload: any) {
  await curatorService.flag(id.value, payload)
  flagModalOpen.value = false
  await load()
}

async function approve() {
  await curatorService.approve(id.value)
  router.push('/moderation/queue')
}

async function reject(feedback: string) {
  await curatorService.reject(id.value, { curator_feedback: feedback })
  router.push('/moderation/queue')
}

async function requestChanges(feedback: string) {
  await curatorService.requestChanges(id.value, { curator_feedback: feedback })
  router.push('/moderation/queue')
}

onMounted(() => {
  refreshAIAvailability()
  load()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8 space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <button class="text-sm text-gray-600 hover:text-gray-900" @click="router.push('/moderation/queue')">
          {{ t('curatorReview.backToQueue') }}
        </button>
        <h1 class="text-2xl font-bold text-gray-900 mt-2">{{ t('curatorReview.title') }}</h1>
      </div>
      <div class="flex items-center gap-2">
        <span class="inline-block" :title="!aiAvailable ? t('curatorReview.aiReview.unavailable') : ''">
          <button
            class="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            :disabled="loading || aiLoading || !detail || !aiAvailable"
            @click="runAIReview"
          >
            {{ aiLoading ? t('curatorReview.aiLoading') : t('curatorReview.aiAssist') }}
          </button>
        </span>
        <button class="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50" :disabled="loading" @click="load">
          {{ t('curatorReview.refresh') }}
        </button>
      </div>
    </div>

    <div v-if="error" class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
      {{ error }}
    </div>
    <div v-if="loading" class="text-gray-600">{{ t('curatorReview.loading') }}</div>

    <div v-if="detail" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <section class="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-5">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-xl font-semibold text-gray-900">{{ (detail as any).heritage_item?.title }}</h2>
            <div class="text-sm text-gray-600 mt-1">{{ t('curatorReview.status', { status: t(`curatorReview.statusMap.${(detail as any).heritage_item?.status}`) }) }}</div>
          </div>
          <button class="px-3 py-2 rounded-lg bg-red-50 text-red-700 hover:bg-red-100" @click="flagModalOpen = true">
            {{ t('curatorReview.flag') }}
          </button>
        </div>

        <div class="mt-4 prose max-w-none">
          <p class="text-gray-800 whitespace-pre-wrap">{{ (detail as any).heritage_item?.description }}</p>
        </div>

        <div class="mt-6 border-t pt-4">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">{{ t('curatorReview.metadataLocation.title') }}</h3>
          <dl class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-4 text-sm">
            <div>
              <dt class="text-gray-500">{{ t('curatorReview.metadataLocation.type') }}</dt>
              <dd class="font-medium text-gray-900">{{ (detail as any).heritage_item?.heritage_type?.name || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">{{ t('curatorReview.metadataLocation.category') }}</dt>
              <dd class="font-medium text-gray-900">{{ (detail as any).heritage_item?.heritage_category?.name || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">{{ t('curatorReview.metadataLocation.parish') }}</dt>
              <dd class="font-medium text-gray-900">{{ (detail as any).heritage_item?.parish?.name || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">{{ t('curatorReview.metadataLocation.historicalPeriod') }}</dt>
              <dd class="font-medium text-gray-900 capitalize">{{ (detail as any).heritage_item?.historical_period?.replace('_', ' ') || '-' }}</dd>
            </div>
            <div class="md:col-span-2">
              <dt class="text-gray-500">{{ t('curatorReview.metadataLocation.address') }}</dt>
              <dd class="font-medium text-gray-900">{{ (detail as any).heritage_item?.address || t('curatorReview.metadataLocation.noAddress') }}</dd>
            </div>
            <div class="md:col-span-2" v-if="(detail as any).heritage_item?.location">
               <dt class="text-gray-500">{{ t('curatorReview.metadataLocation.coordinates') }}</dt>
               <dd class="text-sm text-gray-900 mt-1 mb-2">
                 {{ (detail as any).heritage_item.location }}
               </dd>
               <div class="h-64 w-full rounded-lg overflow-hidden border border-gray-200">
                 <MapContainer
                   v-if="parsedLocation"
                   :center="parsedLocation"
                   :zoom="15"
                   :markers="[{
                     id: (detail as any).heritage_item.id,
                     title: (detail as any).heritage_item.title,
                     coordinates: parsedLocation,
                     type: (detail as any).heritage_item.heritage_type?.name,
                     category: (detail as any).heritage_item.heritage_category?.name,
                     image: (detail as any).heritage_item.images?.[0]?.file
                   }]"
                 />
                 <div v-else class="flex items-center justify-center h-full bg-gray-50 text-gray-500">
                   {{ t('curatorReview.metadataLocation.invalidCoordinates') }}
                 </div>
               </div>
            </div>
          </dl>
        </div>

        <div class="mt-6 space-y-6">
          <div v-if="(detail as any).heritage_item?.images?.length">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">{{ t('curatorReview.media.images') }}</h3>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
              <img
                v-for="(img, idx) in (detail as any).heritage_item.images"
                :key="idx"
                :src="img.file"
                class="w-full h-32 object-cover rounded-lg border bg-gray-50"
              />
            </div>
          </div>

          <div v-if="(detail as any).heritage_item?.audio?.length">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">{{ t('curatorReview.media.audio') }}</h3>
            <div class="space-y-3">
              <div
                v-for="(aud, idx) in (detail as any).heritage_item.audio"
                :key="idx"
                class="bg-gray-50 rounded-lg p-3 border"
              >
                <div class="text-xs text-gray-500 mb-1" v-if="aud.caption || aud.file">{{ aud.caption || aud.file.split('/').pop() }}</div>
                <audio controls class="w-full h-8">
                  <source :src="aud.file" />
                  Your browser does not support the audio element.
                </audio>
              </div>
            </div>
          </div>

          <div v-if="(detail as any).heritage_item?.video?.length">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">{{ t('curatorReview.media.video') }}</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                v-for="(vid, idx) in (detail as any).heritage_item.video"
                :key="idx"
                class="bg-gray-50 rounded-lg border overflow-hidden"
              >
                <video controls class="w-full h-48 bg-black">
                  <source :src="vid.file" />
                  Your browser does not support the video element.
                </video>
                <div class="p-2 text-xs text-gray-600 truncate" v-if="vid.caption || vid.file">
                  {{ vid.caption || vid.file.split('/').pop() }}
                </div>
              </div>
            </div>
          </div>

          <div v-if="(detail as any).heritage_item?.documents?.length">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">{{ t('curatorReview.media.documents') }}</h3>
            <ul class="space-y-2">
              <li
                v-for="(doc, idx) in (detail as any).heritage_item.documents"
                :key="idx"
                class="flex items-center justify-between p-3 bg-gray-50 rounded-lg border hover:bg-gray-100 transition"
              >
                <div class="flex items-center gap-3 overflow-hidden">
                  <svg class="h-6 w-6 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <div class="truncate">
                    <div class="text-sm font-medium text-gray-900 truncate">
                      {{ doc.caption || doc.file.split('/').pop() }}
                    </div>
                  </div>
                </div>
                <a
                  :href="doc.file"
                  target="_blank"
                  class="ml-4 text-sm font-medium text-indigo-600 hover:text-indigo-900"
                >
                  {{ t('curatorReview.media.view') }}
                </a>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <div class="space-y-4">
        <section v-if="aiError || aiReview" class="bg-white border border-gray-200 rounded-xl p-5">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900">{{ t('curatorReview.aiReview.title') }}</h3>
            <span class="inline-block" :title="!aiAvailable ? t('curatorReview.aiReview.unavailable') : ''">
              <button
                type="button"
                class="text-sm px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50"
                :disabled="aiLoading || loading || !aiAvailable"
                @click="runAIReview"
              >
                {{ aiLoading ? t('curatorReview.aiReview.generating') : t('curatorReview.aiReview.regenerate') }}
              </button>
            </span>
          </div>

          <div v-if="aiError" class="mt-3 bg-red-50 border border-red-200 text-red-800 px-3 py-2 rounded-lg">
            {{ aiError }}
          </div>

          <div v-if="aiReview" class="mt-4 space-y-3">
            <div v-if="aiReview.missing_fields?.length">
              <div class="text-sm font-semibold text-gray-700 mb-1">{{ t('curatorReview.aiReview.missingFields') }}</div>
              <ul class="list-disc pl-5 text-sm text-gray-800">
                <li v-for="(f, idx) in aiReview.missing_fields" :key="idx">{{ f }}</li>
              </ul>
            </div>

            <div v-if="aiReview.risk_flags?.length">
              <div class="text-sm font-semibold text-gray-700 mb-1">{{ t('curatorReview.aiReview.riskFlags') }}</div>
              <ul class="list-disc pl-5 text-sm text-gray-800">
                <li v-for="(f, idx) in aiReview.risk_flags" :key="idx">{{ f }}</li>
              </ul>
            </div>

            <div v-if="aiReview.curator_feedback_draft">
              <div class="text-sm font-semibold text-gray-700 mb-1">{{ t('curatorReview.aiReview.feedbackDraft') }}</div>
              <textarea
                v-model="aiReview.curator_feedback_draft"
                rows="4"
                class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500"
              />
              <button
                v-if="canCopy"
                type="button"
                class="mt-2 text-sm px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50"
                @click="copyAIFeedback"
              >
                {{ t('curatorReview.aiReview.copy') }}
              </button>
            </div>
          </div>
        </section>

        <QualityScoreCard v-model="score" :disabled="loading" @save="saveScore" />
        <ReviewChecklistComponent
          :checklist="checklist"
          :responses="checklistResponses"
          :disabled="loading"
          @update:responses="(v) => (checklistResponses = v)"
          @save="saveChecklist"
        />
        <CuratorNotesEditor :notes="detail.curator_notes" :disabled="loading" @add="addNote" />
        <ReviewActions :disabled="loading" @approve="approve" @reject="reject" @requestChanges="requestChanges" />
        <VersionHistoryTimeline :versions="detail.versions" />
      </div>
    </div>

    <FlagContributionModal :open="flagModalOpen" @close="flagModalOpen = false" @submit="flagContribution" />
  </div>
</template>

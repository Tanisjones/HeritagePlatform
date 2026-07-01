<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { lessonPlanService } from '@/services/api'
import { useAsyncAction } from '@/composables/useAsyncAction'
import { unwrapResults } from '@/utils/pagination'
import { useConfirm, useToast } from '@/composables/useDialogs'
import type { LessonPlan } from '@/types/heritage'
import AppButton from '@/components/common/AppButton.vue'
import AppCard from '@/components/common/AppCard.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'

const router = useRouter()
const { t } = useI18n()
const { confirm } = useConfirm()
const toast = useToast()
const { loading, error, run } = useAsyncAction()

const plans = ref<LessonPlan[]>([])

async function load() {
  await run(async () => {
    const res = await lessonPlanService.list()
    plans.value = unwrapResults<LessonPlan>(res.data)
  })
}

function createNew() {
  router.push({ name: 'lesson-plan-new' })
}

function edit(plan: LessonPlan) {
  router.push({ name: 'lesson-plan-edit', params: { id: plan.id } })
}

async function duplicate(plan: LessonPlan) {
  try {
    const res = await lessonPlanService.duplicate(plan.id)
    toast.success(t('lessonPlans.duplicated'))
    router.push({ name: 'lesson-plan-edit', params: { id: res.data.id } })
  } catch {
    toast.error(t('common.errorGeneric'))
  }
}

async function remove(plan: LessonPlan) {
  if (!(await confirm({ message: t('lessonPlans.confirmDelete'), danger: true }))) return
  try {
    await lessonPlanService.delete(plan.id)
    plans.value = plans.value.filter((p) => p.id !== plan.id)
  } catch {
    toast.error(t('common.errorGeneric'))
  }
}

const statusClass: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  review: 'bg-yellow-100 text-yellow-800',
  published: 'bg-secondary-100 text-secondary-800',
  archived: 'bg-gray-100 text-gray-500',
}

onMounted(load)
</script>

<template>
  <div class="max-w-6xl mx-auto p-5 space-y-5">
    <div class="flex items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-display font-bold text-gray-900">{{ t('lessonPlans.title') }}</h1>
        <p class="mt-1 text-gray-600">{{ t('lessonPlans.subtitle') }}</p>
      </div>
      <AppButton @click="createNew">{{ t('lessonPlans.create') }}</AppButton>
    </div>

    <ErrorBanner :message="error" @retry="load" />

    <div v-if="loading" class="flex justify-center py-16">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>

    <EmptyState
      v-else-if="plans.length === 0"
      :title="t('lessonPlans.empty.title')"
      :description="t('lessonPlans.empty.description')"
    >
      <AppButton @click="createNew">{{ t('lessonPlans.create') }}</AppButton>
    </EmptyState>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <AppCard v-for="plan in plans" :key="plan.id" hoverable>
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-semibold text-gray-900">{{ plan.title }}</h3>
          <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="statusClass[plan.status]">
            {{ t(`lessonPlans.status.${plan.status}`) }}
          </span>
        </div>
        <p v-if="plan.summary" class="mt-2 text-sm text-gray-600 line-clamp-2">{{ plan.summary }}</p>
        <div class="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
          <span v-if="plan.subject">{{ plan.subject }}</span>
          <span v-if="plan.grade_level">· {{ t('lessonPlans.gradeShort') }} {{ plan.grade_level }}</span>
          <span>· {{ plan.activities.length }} {{ t('lessonPlans.activitiesCount') }}</span>
        </div>
        <div class="mt-4 flex gap-2">
          <AppButton size="sm" @click="edit(plan)">{{ t('common.edit') }}</AppButton>
          <AppButton size="sm" variant="ghost" @click="duplicate(plan)">{{ t('lessonPlans.duplicate') }}</AppButton>
          <AppButton size="sm" variant="ghost" class="!text-red-600" @click="remove(plan)">{{ t('common.delete') }}</AppButton>
        </div>
      </AppCard>
    </div>
  </div>
</template>

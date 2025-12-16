<script setup lang="ts">
import { ref } from 'vue';
import ContributionForm from '@/components/contribution/ContributionForm.vue';
import { useI18n } from 'vue-i18n';
import AppCard from '@/components/common/AppCard.vue'
import AppButton from '@/components/common/AppButton.vue'
import { useRouter } from 'vue-router'

const { t } = useI18n();
const router = useRouter()
const currentStep = ref(1);

const handleStepChange = (step: number) => {
  currentStep.value = step;
};
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">{{ t('contribute.title') }}</h1>

    <AppCard v-if="currentStep === 1" class="mb-8">
      <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">{{ t('routesUi.createRouteTitle') }}</h2>
          <p class="text-sm text-gray-600 mt-1">
            {{ t('routesUi.createRouteDesc') }}
          </p>
        </div>
        <AppButton @click="router.push('/routes/new')">{{ t('routesUi.createRoute') }}</AppButton>
      </div>
    </AppCard>

    <ContributionForm @step-change="handleStepChange" />
  </div>
</template>

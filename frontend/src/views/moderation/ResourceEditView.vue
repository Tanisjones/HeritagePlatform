<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { resourceService } from '@/services/api'; // Ensure this matches existing exports
import api from '@/services/api';
import { useI18n } from 'vue-i18n';
import { useToast } from '@/composables/useDialogs';
import { useFileUpload } from '@/composables/useFileUpload';
import { useCityStore } from '@/stores/city';
import ErrorBanner from '@/components/common/ErrorBanner.vue';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import LocationPickerMap from '@/components/map/LocationPickerMap.vue';

const { t } = useI18n();
const toast = useToast();
// Shared XHR uploader (progress + abort); `uploading` replaces the old uploadingImage flag.
const { uploading: uploadingImage, uploadFile } = useFileUpload();
const route = useRoute();
const router = useRouter();
const id = route.params.id as string;

const loading = ref(false);
const saving = ref(false);
const error = ref<string | null>(null);

const cityStore = useCityStore();
const cityDefaultLngLat = (): [number, number] => {
  const c = cityStore.activeCity?.center?.coordinates;
  return Array.isArray(c) ? [c[0], c[1]] : [-78.65, -1.67];
};
const cityDefaultLatLng = () => {
  const [lng, lat] = cityDefaultLngLat();
  return { lat, lng };
};

const form = reactive({
  title: '',
  description: '',
  heritage_type: null as number | null,
  heritage_category: null as string | null,
  parish: null as number | null,
  address: '',
  historical_period: '',
  external_registry_url: '',
  video_url: '', // Some items might have this locally
  location: { type: 'Point', coordinates: cityDefaultLngLat() },
  main_image: null as string | null
});

const formLocation = ref(cityDefaultLatLng());
const zoom = ref(13);
const main_image_url = ref<string | null>(null);

// Data sources
const parishes = ref<any[]>([]);
const heritageTypes = ref<any[]>([]);
const heritageCategories = ref<any[]>([]);
const historicalPeriods = [
    'pre-columbian',
    'colonial',
    'republican',
    'contemporary',
    'unknown',
];

const fetchData = async () => {
  loading.value = true;
  error.value = null;
  try {
    const [itemRes, parishesRes, typesRes, categoriesRes] = await Promise.all([
      resourceService.get(id),
      api.get('/parishes/'),
      api.get('/types/'),
      api.get('/categories/all/')
    ]);

    const item = itemRes.data;
    form.title = item.title;
    form.description = item.description;
    form.heritage_type = item.heritage_type?.id || item.heritage_type;
    form.heritage_category = item.heritage_category?.id || item.heritage_category;
    form.parish = item.parish?.id || item.parish;
    form.address = item.address;
    form.historical_period = item.historical_period;
    form.external_registry_url = item.external_registry_url;
    
    // Handle main image
    if (item.main_image) {
       // Since DetailSerializer returns object
       form.main_image = item.main_image.id;
       main_image_url.value = item.main_image.file;
    }

    if (item.location && item.location.coordinates) {
      form.location = item.location;
      formLocation.value = {
        lat: item.location.coordinates[1],
        lng: item.location.coordinates[0]
      };
    }

    parishes.value = parishesRes.data.results || parishesRes.data;
    heritageTypes.value = typesRes.data.results || typesRes.data;
    heritageCategories.value = categoriesRes.data.results || categoriesRes.data;

  } catch (err) {
    console.error('Error loading data:', err);
    error.value = t('common.errorLoading');
  } finally {
    loading.value = false;
  }
};

const onLocationUpdate = ([lat, lng]: [number, number]) => {
  formLocation.value = { lat, lng };
  form.location = { type: 'Point', coordinates: [lng, lat] };
};

const handleImageUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files || !target.files[0]) return;

  const file = target.files[0];

  // Preview
  const reader = new FileReader();
  reader.onload = (e) => {
    if (e.target?.result) {
      main_image_url.value = e.target.result as string;
    }
  };
  reader.readAsDataURL(file);

  // Upload via the shared uploader (manages the `uploadingImage` flag).
  try {
     form.main_image = await uploadFile(file, 'image');
  } catch (err) {
     console.error('Upload failed', err);
     toast.error(t('common.errorUploading'));
  }
};

const save = async () => {
  saving.value = true;
  try {
    if (uploadingImage.value) {
       toast.info(t('common.waitUpload'));
       return;
    }
    // Clean payload
    const payload = { ...form };
    delete (payload as any).video_url; // Remove field not in model
    
    // Ensure heritage_type and category are valid IDs (not null if possible, though model handles validation)
    if (!payload.heritage_type) delete (payload as any).heritage_type;
    if (!payload.heritage_category) delete (payload as any).heritage_category;
    if (!payload.parish) delete (payload as any).parish;
    
    await resourceService.update(id, payload);
    toast.success(t('common.saved'));
    router.push('/moderation/resources');
  } catch (err: any) {
    console.error('Error saving:', err);
    if (err.response && err.response.data) {
        console.error('Validation errors:', err.response.data);
    }
    toast.error(t('common.errorSaving'));
  } finally {
    saving.value = false;
  }
};

const cancel = () => {
  router.push('/moderation/resources');
};

onMounted(fetchData);
</script>

<template>
  <div class="max-w-4xl mx-auto bg-white shadow-lg rounded-lg overflow-hidden">
    <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
      <h1 class="text-xl font-bold text-gray-800">{{ t('moderation.resources.editTitle') }}</h1>
      <button @click="cancel" class="text-gray-500 hover:text-gray-700">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <ErrorBanner v-if="error" :message="error" class="m-6" @retry="fetchData" />

    <div v-else-if="loading" class="p-8 text-center text-gray-500">
      {{ t('curatorReview.loading') }}
    </div>

    <form v-else @submit.prevent="save" class="p-6 space-y-6">
      
      <!-- Basic Info -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.title') }}</label>
          <input v-model="form.title" type="text" required class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" />
        </div>

        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.description') }}</label>
          <textarea v-model="form.description" rows="5" required class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"></textarea>
        </div>

        <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.mainImage') }}</label>
            <div class="flex items-center space-x-6">
                <div v-if="main_image_url" class="relative h-32 w-32 rounded-lg overflow-hidden bg-gray-100 border border-gray-200 shadow-sm flex-shrink-0">
                    <img :src="main_image_url" class="h-full w-full object-cover" />
                </div>
                <div class="flex-1">
                    <input type="file" accept="image/*" @change="handleImageUpload" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100" />
                    <p class="mt-1 text-xs text-gray-500" v-if="uploadingImage">{{ t('common.loading') }}</p>
                </div>
            </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.heritageType') }}</label>
          <select v-model="form.heritage_type" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
            <option :value="null">{{ t('common.select') }}</option>
            <option v-for="tval in heritageTypes" :key="tval.id" :value="tval.id">{{ tval.name }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.category') }}</label>
          <select v-model="form.heritage_category" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
            <option :value="null">{{ t('common.select') }}</option>
            <option v-for="c in heritageCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>

        <div>
           <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.historicalPeriod') }}</label>
           <select v-model="form.historical_period" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
              <option value="">{{ t('common.select') }}</option>
              <option v-for="p in historicalPeriods" :key="p" :value="p">{{ t('periods.' + p.replace('-', '_')) }}</option>
           </select>
        </div>

        <div>
           <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.externalUrl') }}</label>
           <input v-model="form.external_registry_url" type="url" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" />
        </div>
      </div>

      <!-- Location -->
      <div class="border-t border-gray-200 pt-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">{{ t('common.location') }}</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.parish') }}</label>
            <select v-model="form.parish" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
              <option :value="null">{{ t('common.select') }}</option>
              <option v-for="p in parishes" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.address') }}</label>
            <input v-model="form.address" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" />
          </div>
        </div>
        
        <div class="h-96 rounded-lg overflow-hidden border border-gray-300 relative z-0">
           <LocationPickerMap
             :latlng="[formLocation.lat, formLocation.lng]"
             :zoom="zoom"
             @update:latlng="onLocationUpdate"
           />
        </div>
        <p class="text-xs text-gray-500 mt-2">{{ t('common.clickToUpdateMap') }}</p>
      </div>

      <!-- Actions -->
      <div class="flex justify-end gap-3 border-t border-gray-200 pt-6">
        <button type="button" @click="cancel" class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50">
          {{ t('common.cancel') }}
        </button>
        <button type="submit" :disabled="saving" class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 flex items-center">
          <BaseSpinner v-if="saving" class="-ml-1 mr-2 h-4 w-4 text-white" />
          {{ t('common.save') }}
        </button>
      </div>

    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { resourceService } from '@/services/api'; // Ensure this matches existing exports
import api from '@/services/api';
import { useI18n } from 'vue-i18n';
import { LMap, LTileLayer, LMarker } from "@vue-leaflet/vue-leaflet";
import "leaflet/dist/leaflet.css";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const id = route.params.id as string;

const loading = ref(false);
const saving = ref(false);

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
  location: { type: 'Point', coordinates: [-78.65, -1.67] },
  main_image: null as string | null
});

const formLocation = ref({ lat: -1.67, lng: -78.65 });
const zoom = ref(13);
const center = ref<[number, number]>([-1.67, -78.65]);
const main_image_url = ref<string | null>(null);
const uploadingImage = ref(false);

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
      center.value = [formLocation.value.lat, formLocation.value.lng];
    }

    parishes.value = parishesRes.data.results || parishesRes.data;
    heritageTypes.value = typesRes.data.results || typesRes.data;
    heritageCategories.value = categoriesRes.data.results || categoriesRes.data;

  } catch (error) {
    console.error('Error loading data:', error);
    alert(t('common.errorLoading'));
  } finally {
    loading.value = false;
  }
};

const handleMapClick = (e: any) => {
  formLocation.value = e.latlng;
  form.location = { 
    type: 'Point', 
    coordinates: [e.latlng.lng, e.latlng.lat] 
  };
};

const uploadOneFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_type', 'image');
  
  const response = await api.post('/media/', formData);
  return response.data.id;
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

  // Upload
  uploadingImage.value = true;
  try {
     const id = await uploadOneFile(file);
     form.main_image = id;
  } catch (err) {
     console.error('Upload failed', err);
     alert(t('common.errorUploading'));
  } finally {
     uploadingImage.value = false;
  }
};

const save = async () => {
  saving.value = true;
  try {
    if (uploadingImage.value) {
       alert(t('common.waitUpload'));
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
    alert(t('common.saved'));
    router.push('/moderation/resources');
  } catch (error: any) {
    console.error('Error saving:', error);
    if (error.response && error.response.data) {
        console.error('Validation errors:', error.response.data);
        alert(`Error al guardar: ${JSON.stringify(error.response.data)}`);
    } else {
        alert(t('common.errorSaving'));
    }
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

    <div v-if="loading" class="p-8 text-center text-gray-500">
      {{ t('curatorReview.loading') }}
    </div>

    <form v-else @submit.prevent="save" class="p-6 space-y-6">
      
      <!-- Basic Info -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.title') }}</label>
          <input v-model="form.title" type="text" required class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
        </div>

        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.description') }}</label>
          <textarea v-model="form.description" rows="5" required class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"></textarea>
        </div>

        <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.mainImage') }}</label>
            <div class="flex items-center space-x-6">
                <div v-if="main_image_url" class="relative h-32 w-32 rounded-lg overflow-hidden bg-gray-100 border border-gray-200 shadow-sm flex-shrink-0">
                    <img :src="main_image_url" class="h-full w-full object-cover" />
                </div>
                <div class="flex-1">
                    <input type="file" accept="image/*" @change="handleImageUpload" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100" />
                    <p class="mt-1 text-xs text-gray-500" v-if="uploadingImage">{{ t('common.loading') }}</p>
                </div>
            </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.heritageType') }}</label>
          <select v-model="form.heritage_type" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
            <option :value="null">{{ t('common.select') }}</option>
            <option v-for="tval in heritageTypes" :key="tval.id" :value="tval.id">{{ tval.name }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.category') }}</label>
          <select v-model="form.heritage_category" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
            <option :value="null">{{ t('common.select') }}</option>
            <option v-for="c in heritageCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>

        <div>
           <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.historicalPeriod') }}</label>
           <select v-model="form.historical_period" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
              <option value="">{{ t('common.select') }}</option>
              <option v-for="p in historicalPeriods" :key="p" :value="p">{{ t('periods.' + p.replace('-', '_')) }}</option>
           </select>
        </div>

        <div>
           <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.externalUrl') }}</label>
           <input v-model="form.external_registry_url" type="url" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
        </div>
      </div>

      <!-- Location -->
      <div class="border-t border-gray-200 pt-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">{{ t('common.location') }}</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.parish') }}</label>
            <select v-model="form.parish" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
              <option :value="null">{{ t('common.select') }}</option>
              <option v-for="p in parishes" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('common.address') }}</label>
            <input v-model="form.address" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
          </div>
        </div>
        
        <div class="h-96 rounded-lg overflow-hidden border border-gray-300 relative z-0">
           <l-map ref="map" v-model:zoom="zoom" :center="center" @click="handleMapClick">
              <l-tile-layer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" layer-type="base" name="OpenStreetMap"></l-tile-layer>
              <l-marker :lat-lng="[formLocation.lat, formLocation.lng] as [number, number]"></l-marker>
           </l-map>
        </div>
        <p class="text-xs text-gray-500 mt-2">{{ t('common.clickToUpdateMap') }}</p>
      </div>

      <!-- Actions -->
      <div class="flex justify-end gap-3 border-t border-gray-200 pt-6">
        <button type="button" @click="cancel" class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50">
          {{ t('common.cancel') }}
        </button>
        <button type="submit" :disabled="saving" class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 flex items-center">
          <svg v-if="saving" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ t('common.save') }}
        </button>
      </div>

    </form>
  </div>
</template>

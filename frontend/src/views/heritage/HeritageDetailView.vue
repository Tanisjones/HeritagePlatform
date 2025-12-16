<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/services/api';
import type { HeritageItem } from '@/types/heritage';
import AnnotationList from '@/components/annotations/AnnotationList.vue';
import { LMap, LTileLayer, LMarker } from "@vue-leaflet/vue-leaflet";
import "leaflet/dist/leaflet.css";
import { useI18n } from 'vue-i18n';

const { t, te, locale } = useI18n();
const route = useRoute();

interface ViewableResource {
    type: 'video' | 'audio' | 'image' | 'document';
    url: string;
    id: string;
    title?: string;
  mimeType?: string;
  text_content?: string;
}

const translateLom = (category: string, value: string | undefined | null, fallbackKey = 'heritage.detail.na') => {
  if (!value) return t(fallbackKey);
  const key = `lom.${category}.${value}`;
  return te(key) ? t(key) : value.replace(/_/g, ' ');
};

const item = ref<HeritageItem | null>(null);
const loading = ref(true);
const zoom = ref(15);
const center = ref<[number, number]>([-1.67, -78.65]);

type RelationTargetType = 'media' | 'item' | 'url';

const relationTargetType = ref<RelationTargetType>('media');
const relationKind = ref('is_similar_to');
const relationTargetMediaId = ref<string>('');
const relationTargetHeritageItemId = ref<string>('');
const relationTargetUrl = ref<string>('');
const relationDescription = ref<string>('');
const relationSaving = ref(false);
const relationError = ref<string | null>(null);

const scormDownloading = ref(false);
const scormError = ref<string | null>(null);

// Media Viewer State
const activeMedia = ref<ViewableResource | null>(null);

const educationalEntries = computed(() => {
  const educational = item.value?.lom_metadata?.educational;
  if (!educational) return [];
  if (Array.isArray(educational)) {
      return educational;
  }
  return [educational]; 
});

const rightsMetadata = computed(() => {
    return item.value?.lom_metadata?.rights;
});

const createdAtLabel = computed(() => {
  const raw = item.value?.created_at;
  if (!raw) return '';
  const date = new Date(raw);
  const localeCode = locale.value === 'en' ? 'en-US' : 'es-ES';
  return date.toLocaleDateString(localeCode, { year: 'numeric', month: 'long', day: 'numeric' });
});

const getResourceType = computed(() => {
    if (!item.value) return null;
    const educational = item.value.lom_metadata?.educational;
    if (!educational) return null;
    if (Array.isArray(educational)) {
        return educational[0]?.learning_resource_type ?? null;
    }
    return educational.learning_resource_type || null;
});

// Helper to resolve media URLs
const resolveUrl = (url: string) => {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    // If it's a relative path starting with /media, prepend backend host
    if (url.startsWith('/media')) {
         // Assuming backend is on port 8000 for local dev. 
         // ideally this comes from env, stripping /api/v1 if needed
         return `http://localhost:8000${url}`;
    }
    return url;
}

// Aggregate all media into a uniform list
const allMedia = computed<ViewableResource[]>(() => {
    if (!item.value) return [];
    
    const media: ViewableResource[] = [];

     if (item.value.main_image) {
      media.push({ type: 'image', url: item.value.main_image.file, id: item.value.main_image.id, title: item.value.main_image.caption || 'Main Image', mimeType: item.value.main_image.mime_type });
    }
    
    if (item.value.video) {
      item.value.video.forEach(v => media.push({ type: 'video', url: v.file, id: v.id, title: 'Video', mimeType: v.mime_type }));
    }
    if (item.value.audio) {
      item.value.audio.forEach(a => media.push({ type: 'audio', url: a.file, id: a.id, title: 'Audio', mimeType: a.mime_type }));
    }
    if (item.value.images) {
      item.value.images.forEach(i => media.push({ type: 'image', url: i.file, id: i.id, title: i.caption || 'Image', mimeType: i.mime_type }));
    }
    if (item.value.documents) {
      item.value.documents.forEach(d => {
        const isText = (d.mime_type || '').startsWith('text/');
        media.push({
        type: 'document',
        url: d.file,
        id: d.id,
        title: isText ? 'Text' : 'Document',
        mimeType: d.mime_type,
        text_content: d.text_content,
        });
      });
    }
    
    // Add primary image if no images in list but primary exists (edge case)
    if (media.filter(m => m.type === 'image').length === 0 && item.value.primary_image) {
      media.push({ type: 'image', url: item.value.primary_image, id: 'primary', title: 'Cover Image' });
    }

    // Reorder based on Learning Resource Type
    const resourceType = getResourceType.value;
    if (resourceType === 'narrative_text' || resourceType === 'report' || resourceType === 'questionnaire') {
        // Prioritize documents
        media.sort((a, b) => {
             const aIsDoc = a.type === 'document';
             const bIsDoc = b.type === 'document';
             if (aIsDoc && !bIsDoc) return -1;
             if (!aIsDoc && bIsDoc) return 1;
             return 0;
        });
    }

    return media;
});

const existingLomRelations = computed(() => {
  return item.value?.lom_metadata?.relations ?? [];
});

const selectableTargetMedia = computed(() => {
  const activeId = activeMedia.value?.id;
  return allMedia.value.filter(m => m.id && m.id !== activeId);
});

const relationKindOptions = [
  { value: 'is_similar_to', labelKey: 'heritage.detail.relationKinds.is_similar_to' },
  { value: 'is_part_of', labelKey: 'heritage.detail.relationKinds.is_part_of' },
  { value: 'has_part', labelKey: 'heritage.detail.relationKinds.has_part' },
  { value: 'is_version_of', labelKey: 'heritage.detail.relationKinds.is_version_of' },
  { value: 'has_version', labelKey: 'heritage.detail.relationKinds.has_version' },
  { value: 'is_format_of', labelKey: 'heritage.detail.relationKinds.is_format_of' },
  { value: 'has_format', labelKey: 'heritage.detail.relationKinds.has_format' },
  { value: 'references', labelKey: 'heritage.detail.relationKinds.references' },
  { value: 'is_referenced_by', labelKey: 'heritage.detail.relationKinds.is_referenced_by' },
  { value: 'requires', labelKey: 'heritage.detail.relationKinds.requires' },
  { value: 'is_required_by', labelKey: 'heritage.detail.relationKinds.is_required_by' },
];

const resolveMediaLabel = (mediaId: string) => {
  const media = allMedia.value.find(m => m.id === mediaId);
  return media?.title || mediaId;
};

const createLomRelation = async () => {
  relationError.value = null;
  if (!item.value?.lom_metadata?.id) {
    relationError.value = t('heritage.detail.relationsMissingLom');
    return;
  }

  const payload: Record<string, any> = {
    lom_general: item.value.lom_metadata.id,
    kind: relationKind.value,
    description: relationDescription.value || '',
  };

  if (relationTargetType.value === 'media') {
    if (!relationTargetMediaId.value) {
      relationError.value = t('heritage.detail.relationsSelectTarget');
      return;
    }
    payload.target_media_file = relationTargetMediaId.value;
  } else if (relationTargetType.value === 'item') {
    if (!relationTargetHeritageItemId.value) {
      relationError.value = t('heritage.detail.relationsSelectTarget');
      return;
    }
    payload.target_heritage_item = relationTargetHeritageItemId.value;
  } else {
    if (!relationTargetUrl.value) {
      relationError.value = t('heritage.detail.relationsSelectTarget');
      return;
    }
    payload.target_url = relationTargetUrl.value;
  }

  try {
    relationSaving.value = true;
    await api.post('/lom-relations/', payload);
    relationTargetMediaId.value = '';
    relationTargetHeritageItemId.value = '';
    relationTargetUrl.value = '';
    relationDescription.value = '';
    await fetchHeritageItem();
  } catch (e: any) {
    const msg = e?.response?.data ? JSON.stringify(e.response.data) : String(e);
    relationError.value = msg;
  } finally {
    relationSaving.value = false;
  }
};

const downloadScorm = async () => {
  if (!item.value?.id) return;
  scormError.value = null;
  try {
    scormDownloading.value = true;
    const baseUrl = api.defaults.baseURL || (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1');
    const downloadUrl = `${String(baseUrl).replace(/\/$/, '')}/education/scorm-packages/${String(item.value.id)}/download/`;

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.target = '_blank';
    link.rel = 'noopener';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (e: any) {
    console.error('SCORM download failed', e);
    scormError.value = t('heritage.detail.downloadScormError');
  } finally {
    scormDownloading.value = false;
  }
};

const selectMedia = (media: ViewableResource) => {
    activeMedia.value = media;
};

const fetchHeritageItem = async () => {
  const id = route.params.id;
  try {
    loading.value = true;
    const response = await api.get(`/heritage-items/${id}/`);
    item.value = response.data;
    if (item.value && item.value.location && item.value.location.coordinates) {
        center.value = [item.value.location.coordinates[1], item.value.location.coordinates[0]];
    }
    // Set initial active media
    if (allMedia.value.length > 0) {
        activeMedia.value = allMedia.value[0] || null;
    }
  } catch (error) {
    console.error('Error fetching heritage item:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchHeritageItem);
</script>

<template>
  <div class="min-h-screen bg-neutral-50 pb-20">
    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center items-center h-screen">
      <div class="relative">
        <div class="absolute inset-0 bg-primary-200 blur-xl opacity-50 rounded-full animate-pulse"></div>
        <svg class="relative animate-spin h-12 w-12 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
    </div>

    <div v-else-if="item">
      <!-- Header Section (Title & Meta) -->
      <div class="bg-white border-b border-gray-100 pt-8 pb-6 px-4 md:px-6">
         <div class="max-w-7xl mx-auto">
             <div class="flex flex-wrap gap-3 mb-4">
                <span class="px-3 py-1 rounded-full bg-primary-100 text-primary-700 text-xs font-bold uppercase tracking-wide">
                  {{ item.heritage_type.name }}
                </span>
                <span class="px-3 py-1 rounded-full bg-neutral-100 text-neutral-600 text-xs font-bold uppercase tracking-wide">
                  {{ item.heritage_category.name }}
                </span>
                <span v-if="getResourceType" class="px-3 py-1 rounded-full bg-secondary-100 text-secondary-700 text-xs font-bold uppercase tracking-wide">
                   {{ translateLom('resource_type', getResourceType) }}
                </span>
             </div>
             
             <h1 class="font-display text-3xl md:text-5xl font-bold text-gray-900 mb-2">
                {{ item.title }}
             </h1>
             
             <div class="flex items-center text-gray-500 text-sm md:text-base font-medium mt-2">
                <svg class="w-4 h-4 mr-1.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
                </svg>
                {{ item.parish?.name || t('heritage.detail.unknownLocation') }}
                <span v-if="item.address" class="mx-2 text-gray-300">•</span>
                <span v-if="item.address">{{ item.address }}</span>
             </div>
         </div>
      </div>

      <!-- Main Resource Viewer Section -->
      <div class="bg-neutral-900 w-full py-8 text-white relative">
          <div class="max-w-5xl mx-auto px-4 md:px-6">
              
              <!-- Viewer Container -->
              <div v-if="activeMedia" class="w-full aspect-video md:aspect-[21/9] lg:aspect-[16/9] max-h-[70vh] bg-black rounded-xl overflow-hidden shadow-2xl relative flex items-center justify-center border border-neutral-800">
                  
                  <!-- Video Render -->
                  <video v-if="activeMedia.type === 'video'" :src="resolveUrl(activeMedia.url)" controls class="w-full h-full object-contain" autoplay></video>
                  
                  <!-- Audio Render -->
                  <div v-else-if="activeMedia.type === 'audio'" class="w-full h-full flex flex-col items-center justify-center p-8 bg-gradient-to-br from-neutral-800 to-neutral-900 relative">
                       <!-- Abstract Background or Cover -->
                       <div class="absolute inset-0 opacity-20 bg-[url('/img/audio-pattern.svg')] bg-cover"></div>
                       <div class="z-10 text-center w-full max-w-md">
                           <div class="w-24 h-24 mx-auto bg-primary-500 rounded-full flex items-center justify-center mb-6 shadow-lg animate-pulse-slow">
                               <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"></path></svg>
                           </div>
                           <h3 class="text-xl font-bold mb-4">{{ activeMedia.title }}</h3>
                           <audio :src="resolveUrl(activeMedia.url)" controls class="w-full"></audio>
                       </div>
                  </div>
                  
                  <!-- Image Render -->
                  <div v-else-if="activeMedia.type === 'image'" class="w-full h-full relative">
                      <img :src="resolveUrl(activeMedia.url)" class="w-full h-full object-contain" :alt="activeMedia.title">
                  </div>
                  
                  <!-- Document/Text Render -->
                  <div v-else-if="activeMedia.type === 'document'" class="w-full h-full bg-neutral-800 flex flex-col">
                      <!-- Text Content (Prioritize over file) -->
                      <div v-if="activeMedia.text_content" class="w-full h-full bg-white p-8 overflow-y-auto prose max-w-none text-gray-800">
                           <h3 v-if="activeMedia.title" class="text-xl font-bold mb-4 border-b pb-2">{{ activeMedia.title }}</h3>
                           <div class="whitespace-pre-wrap font-serif text-lg leading-relaxed">{{ activeMedia.text_content }}</div>
                      </div>

                      <!-- PDF Viewer (iframe) -->
                      <iframe
                        v-else-if="activeMedia.mimeType === 'application/pdf' || (activeMedia.url && activeMedia.url.toLowerCase().endsWith('.pdf')) || (activeMedia.mimeType || '').startsWith('text/')"
                        :src="resolveUrl(activeMedia.url)"
                        class="w-full h-full bg-white"
                        :title="activeMedia.title || t('heritage.detail.document')"
                      ></iframe>

                      <!-- Fallback for other documents -->
                      <div v-else class="w-full h-full flex flex-col items-center justify-center p-4">
                        <svg class="w-16 h-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                        <h3 class="text-lg font-medium text-gray-300 mb-4">{{ activeMedia.title || t('heritage.detail.document') }}</h3>
                        <a :href="resolveUrl(activeMedia.url)" target="_blank" class="px-6 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-colors flex items-center">
                            {{ t('heritage.detail.viewOriginal') }}
                            <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                        </a>
                      </div>
                  </div>
              </div>
              
              <!-- Empty State -->
              <div v-else class="w-full h-64 bg-neutral-800 rounded-xl flex items-center justify-center border border-neutral-700">
                  <span class="text-neutral-500 flex items-center">
                      <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                      {{ t('heritage.detail.noMedia') }}
                  </span>
              </div>
              
              <!-- Media Playlist/Gallery Selector -->
              <div v-if="allMedia.length > 1" class="mt-4 flex gap-3 overflow-x-auto py-2 px-1 custom-scrollbar">
                  <button 
                    v-for="(media, idx) in allMedia" 
                    :key="idx" 
                    @click="selectMedia(media)"
                    class="relative shrink-0 w-24 h-16 rounded-lg overflow-hidden border-2 transition-all duration-200 group"
                    :class="activeMedia?.id === media.id ? 'border-primary-500 ring-2 ring-primary-500/50' : 'border-transparent opacity-60 hover:opacity-100 hover:border-gray-500'"
                  >
                      <!-- Thumbnail Logic -->
                      <img v-if="media.type === 'image'" :src="media.url" class="w-full h-full object-cover">
                      <div v-else class="w-full h-full bg-neutral-800 flex items-center justify-center">
                          <span v-if="media.type === 'video'">🎥</span>
                          <span v-else-if="media.type === 'audio'">🎵</span>
                          <span v-else-if="media.type === 'document'">📄</span>
                      </div>
                      
                      <!-- Type Indicator Overlay -->
                      <div class="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
                         <span class="text-white text-xs font-bold capitalize">{{ media.type }}</span>
                      </div>
                  </button>
              </div>

          </div>
      </div>

      <!-- Main Content Grid (Original) -->
      <div class="max-w-7xl mx-auto px-4 md:px-6 mt-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Left Column: Content -->
        <div class="space-y-8 lg:col-span-2">
          
          <!-- Description Card -->
          <div class="bg-white rounded-2xl shadow-xl p-8 overflow-hidden relative group">
             <!-- Decorative background element -->
             <div class="absolute -top-10 -right-10 w-40 h-40 bg-primary-100 rounded-full blur-3xl opacity-50 group-hover:opacity-75 transition-opacity duration-700"></div>

            <h2 class="font-display text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <span class="bg-primary-100 text-primary-600 p-2 rounded-lg mr-3">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"></path></svg>
              </span>
              {{ t('heritage.detail.about') }}
            </h2>
            <div class="prose prose-lg text-gray-600 leading-relaxed max-w-none">
              {{ item.description }}
            </div>
          </div>

          <!-- Educational Characteristics (Glassy Grid) -->
          <div v-if="educationalEntries.length > 0" class="bg-gradient-to-br from-white to-neutral-50 rounded-2xl shadow-xl p-8 border border-neutral-100">
             <h2 class="font-display text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <span class="bg-secondary-100 text-secondary-600 p-2 rounded-lg mr-3">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
              </span>
              {{ t('heritage.detail.educationalContext') }}
            </h2>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6" v-for="(edu, idx) in educationalEntries" :key="idx">
               <!-- Card Item -->
              <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <span class="text-xs font-bold text-secondary-600 uppercase tracking-wider mb-1 block">{{ t('heritage.detail.resourceType') }}</span>
                <span class="text-gray-900 font-medium capitalize">{{ translateLom('resource_type', edu.learning_resource_type, 'heritage.detail.na') }}</span>
              </div>
               <!-- Card Item -->
              <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <span class="text-xs font-bold text-secondary-600 uppercase tracking-wider mb-1 block">{{ t('heritage.detail.difficulty') }}</span>
                <span class="text-gray-900 font-medium capitalize">{{ translateLom('difficulty', edu.difficulty, 'heritage.detail.unspecified') }}</span>
              </div>
               <!-- Card Item -->
              <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <span class="text-xs font-bold text-secondary-600 uppercase tracking-wider mb-1 block">{{ t('heritage.detail.targetAudience') }}</span>
                <span class="text-gray-900 font-medium capitalize">{{ translateLom('audience', edu.intended_end_user_role, 'heritage.detail.general') }}</span>
              </div>
               <!-- Card Item -->
              <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <span class="text-xs font-bold text-secondary-600 uppercase tracking-wider mb-1 block">{{ t('heritage.detail.learningTime') }}</span>
                <span class="text-gray-900 font-medium">{{ edu.typical_learning_time || t('heritage.detail.selfPaced') }}</span>
              </div>
            </div>
          </div>

          <!-- Rights & Info -->
          <div v-if="rightsMetadata" class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white rounded-2xl p-6 shadow-lg border-l-4 border-primary-500">
               <h3 class="text-lg font-bold text-gray-900 mb-2">{{ t('heritage.detail.rightsUsage') }}</h3>
               <p class="text-gray-600 text-sm mb-1">
                 {{ t('heritage.detail.copyright') }}: <span class="font-medium text-gray-900">{{ rightsMetadata.copyright_and_other_restrictions ? t('heritage.detail.restricted') : t('heritage.detail.openAccess') }}</span>
               </p>
               <p class="text-gray-600 text-sm">
                 {{ t('heritage.detail.cost') }}: <span class="font-medium text-gray-900">{{ rightsMetadata.cost ? t('heritage.detail.paid') : t('heritage.detail.free') }}</span>
               </p>
            </div>
             <div class="bg-white rounded-2xl p-6 shadow-lg border-l-4 border-secondary-500">
               <h3 class="text-lg font-bold text-gray-900 mb-2">{{ t('heritage.detail.metadata') }}</h3>
                <p class="text-gray-600 text-sm mb-1">
                 {{ t('heritage.detail.language') }}: <span class="font-medium text-gray-900 uppercase">{{ item.lom_metadata?.language || 'es' }}</span>
               </p>
               <p class="text-gray-600 text-sm truncate">
                 {{ t('heritage.detail.coverage') }}: <span class="font-medium text-gray-900">{{ item.lom_metadata?.coverage || t('heritage.detail.global') }}</span>
               </p>
            </div>
          </div>

          <!-- Comments/Annotations Area -->
          <div class="bg-white rounded-2xl shadow-xl p-8">
            <h2 class="font-display text-2xl font-bold text-gray-900 mb-6">{{ t('heritage.detail.communityInsights') }}</h2>
            <AnnotationList v-if="item.id" :heritage-item-id="item.id" />
          </div>

        </div>

        <!-- Right Column: Map & Actions -->
        <div class="lg:col-span-1 space-y-6">
          
          <!-- Map Card -->
          <div v-if="item.location" class="bg-white p-2 rounded-2xl shadow-xl">
             <div class="h-64 md:h-80 w-full rounded-xl overflow-hidden relative z-0">
                 <l-map ref="map" v-model:zoom="zoom" :center="center" :use-global-leaflet="false">
                    <l-tile-layer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                    layer-type="base" name="OpenStreetMap"></l-tile-layer>
                    <l-marker :lat-lng="center"></l-marker>
                </l-map>
             </div>
             <div class="p-4">
               <h3 class="font-bold text-gray-900">{{ t('heritage.detail.exploreLocation') }}</h3>
               <p class="text-sm text-gray-500 mt-1 flex items-start">
                  <svg class="w-4 h-4 mr-1 text-primary-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path></svg>
                  {{ item.address }}
               </p>
               <button class="w-full mt-4 bg-gray-900 text-white py-2 rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors">
                 {{ t('heritage.detail.getDirections') }}
               </button>
             </div>
          </div>

          <!-- Quick Stats / Sticky Sidebar placeholder -->
          <div class="bg-secondary-50 border border-secondary-100 rounded-2xl p-6 shadow-sm">
            <h3 class="font-display text-lg font-bold text-secondary-900 mb-4">{{ t('heritage.detail.quickFacts') }}</h3>
            <ul class="space-y-4">
              <li class="flex items-center justify-between text-sm">
                <span class="text-secondary-600">{{ t('heritage.detail.idReference') }}</span>
                <span class="font-mono text-secondary-800 font-medium">{{ item.id }}</span>
              </li>
              <li class="flex items-center justify-between text-sm">
                 <span class="text-secondary-600">{{ t('heritage.detail.created') }}</span>
                 <span class="text-secondary-800 font-medium">{{ createdAtLabel }}</span>
              </li>
              <li class="pt-4 border-t border-secondary-200">
                <button class="w-full bg-secondary-600 text-white py-2.5 rounded-lg font-medium hover:bg-secondary-700 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                  {{ t('heritage.detail.bookmark') }}
                </button>
              </li>

              <li>
                <button
                  class="w-full bg-primary-600 text-white py-2.5 rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-60"
                  :disabled="scormDownloading"
                  @click="downloadScorm"
                >
                  {{ scormDownloading ? t('heritage.detail.downloadingScorm') : t('heritage.detail.downloadScorm') }}
                </button>
                <div v-if="scormError" class="text-sm text-red-600 mt-2">{{ scormError }}</div>
              </li>
            </ul>
          </div>

          <!-- Relations (LOM) -->
          <div class="bg-white rounded-2xl p-6 shadow-xl border border-neutral-100">
            <h3 class="font-display text-lg font-bold text-gray-900 mb-4">{{ t('heritage.detail.relationsTitle') }}</h3>

            <div v-if="existingLomRelations.length === 0" class="text-sm text-gray-500">
              {{ t('heritage.detail.relationsNone') }}
            </div>

            <ul v-else class="space-y-3">
              <li v-for="rel in existingLomRelations" :key="rel.id" class="text-sm text-gray-700">
                <span class="font-medium text-gray-900">{{ te(`heritage.detail.relationKinds.${rel.kind}`) ? t(`heritage.detail.relationKinds.${rel.kind}`) : rel.kind }}</span>
                <span class="text-gray-500">→</span>
                <router-link
                  v-if="rel.target_heritage_item"
                  :to="`/heritage/${rel.target_heritage_item}`"
                  class="text-primary-600 hover:text-primary-800 font-medium"
                >
                  {{ rel.target_heritage_item }}
                </router-link>
                <span v-else-if="rel.target_media_file" class="font-medium">
                  {{ resolveMediaLabel(rel.target_media_file) }}
                </span>
                <a v-else-if="rel.target_url" :href="rel.target_url" target="_blank" rel="noopener" class="text-primary-600 hover:text-primary-800 font-medium">
                  {{ rel.target_url }}
                </a>
                <span v-else class="text-gray-500">—</span>
                <div v-if="rel.description" class="text-xs text-gray-500 mt-1">{{ rel.description }}</div>
              </li>
            </ul>

            <div class="mt-6 pt-6 border-t border-neutral-200">
              <h4 class="font-semibold text-gray-900 mb-3">{{ t('heritage.detail.relationsAdd') }}</h4>

              <div class="flex items-center gap-4 text-sm mb-4">
                <label class="inline-flex items-center gap-2">
                  <input type="radio" class="text-primary-600" value="media" v-model="relationTargetType" />
                  {{ t('heritage.detail.relationsTargetMedia') }}
                </label>
                <label class="inline-flex items-center gap-2">
                  <input type="radio" class="text-primary-600" value="item" v-model="relationTargetType" />
                  {{ t('heritage.detail.relationsTargetItem') }}
                </label>
                <label class="inline-flex items-center gap-2">
                  <input type="radio" class="text-primary-600" value="url" v-model="relationTargetType" />
                  {{ t('heritage.detail.relationsTargetUrl') }}
                </label>
              </div>

              <div class="space-y-3">
                <div>
                  <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1">{{ t('heritage.detail.relationsKind') }}</label>
                  <select v-model="relationKind" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                    <option v-for="opt in relationKindOptions" :key="opt.value" :value="opt.value">
                      {{ te(opt.labelKey) ? t(opt.labelKey) : opt.value }}
                    </option>
                  </select>
                </div>

                <div v-if="relationTargetType === 'media'">
                  <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1">{{ t('heritage.detail.relationsTarget') }}</label>
                  <select v-model="relationTargetMediaId" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" :disabled="selectableTargetMedia.length === 0">
                    <option value="">{{ t('heritage.detail.relationsChoose') }}</option>
                    <option v-for="m in selectableTargetMedia" :key="m.id" :value="m.id">{{ m.title || m.id }}</option>
                  </select>
                  <div v-if="selectableTargetMedia.length === 0" class="text-xs text-gray-500 mt-1">
                    {{ t('heritage.detail.relationsNeedMoreMedia') }}
                  </div>
                </div>

                <div v-else-if="relationTargetType === 'item'">
                  <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1">{{ t('heritage.detail.relationsTarget') }}</label>
                  <input v-model="relationTargetHeritageItemId" type="text" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" :placeholder="t('heritage.detail.relationsItemIdPlaceholder')" />
                </div>

                <div v-else>
                  <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1">{{ t('heritage.detail.relationsTarget') }}</label>
                  <input v-model="relationTargetUrl" type="url" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="https://" />
                </div>

                <div>
                  <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1">{{ t('heritage.detail.relationsDescription') }}</label>
                  <textarea v-model="relationDescription" rows="2" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"></textarea>
                </div>

                <div v-if="relationError" class="text-sm text-red-600">
                  {{ relationError }}
                </div>

                <button
                  class="w-full bg-primary-600 text-white py-2.5 rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-60"
                  :disabled="relationSaving"
                  @click="createLomRelation"
                >
                  {{ relationSaving ? t('heritage.detail.relationsSaving') : t('heritage.detail.relationsSave') }}
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
    
    <!-- Not Found State -->
    <div v-else class="text-center py-20">
      <h2 class="text-2xl font-display font-bold text-gray-900">{{ t('heritage.detail.notFound') }}</h2>
      <p class="text-gray-500 mt-2">{{ t('heritage.detail.notFoundDesc') }}</p>
       <router-link to="/explore" class="inline-block mt-6 text-primary-600 hover:text-primary-800 font-medium">
        &larr; {{ t('heritage.detail.backToExplore') }}
      </router-link>
    </div>
  </div>
</template>

<style scoped>
/* Leaflet map z-index fix */
.leaflet-container {
    z-index: 1;
}

.custom-scrollbar::-webkit-scrollbar {
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: #1a1a1a;
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #666;
}
</style>

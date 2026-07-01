<script setup lang="ts">
/**
 * ContributionForm.vue
 * 
 * Multi-step wizard for submitting new heritage items.
 * Steps:
 * 1. Resource Upload (Image, Audio, Video, Document, or Text)
 * 2. General Information (Title, Description, Classification) - includes AI drafting
 * 3. Location (Point selection on map)
 * 4. Details (Historical period, external links)
 * 5. Educational layer (IEEE-LOM pedagogy) - includes AI metadata generation
 * 6. Review & Submit
 */
import { ref, reactive, computed, onMounted, watch } from 'vue';
import type { HeritageItemContribution, Parish, HeritageType, HeritageCategory } from '@/types/heritage';
import api, { aiService } from '@/services/api';
import { useAIAvailability } from '@/services/aiAvailability'
import AiActionButton from '@/components/common/AiActionButton.vue';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import { LMap, LTileLayer, LMarker } from "@vue-leaflet/vue-leaflet";
import "leaflet/dist/leaflet.css";
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

// --- State ---
const { t, locale } = useI18n();
const router = useRouter();
const emit = defineEmits(['step-change']);

const currentStep = ref(1);

watch(currentStep, (newStep) => {
  emit('step-change', newStep);
});

const totalSteps = 6;
const submittedSuccess = ref(false);
const queuedOffline = ref(false);

type ContributionResourceType = 'image' | 'audio' | 'video' | 'document' | 'text';
const resourceType = ref<ContributionResourceType>('text');

const contribution = reactive<Partial<HeritageItemContribution>>({
  title: '',
  description: '',
  location: { type: 'Point', coordinates: [-78.65, -1.67] }, // Default to Riobamba
  address: '',
  parish: null,
  heritage_type: null,
  heritage_category: null,
  historical_period: '',
  external_registry_url: '',
  images: [],
  audio: [],
  video: [],
  documents: [],
});

// --- Educational (IEEE-LOM §5) layer captured in step 5 ---
// Sent to the backend under `educational` on the contribution POST; the API
// validates it through LOMEducationalSerializer and attaches it to the item's
// LOM. All fields are optional — blanks are stripped before submit.
interface EducationalDraft {
  learning_resource_type: string;
  difficulty: string;
  typical_age_range: string;
  typical_learning_time: string;
  context: string;
  interactivity_type: string;
  intended_end_user_role: string;
  pedagogical_approach: string;
  learning_objectives: string[];
  prerequisites: string;
  competencies: string;
}
const createEducationalDraft = (): EducationalDraft => ({
  learning_resource_type: '',
  difficulty: '',
  typical_age_range: '',
  typical_learning_time: '',
  context: '',
  interactivity_type: '',
  intended_end_user_role: '',
  pedagogical_approach: '',
  learning_objectives: [],
  prerequisites: '',
  competencies: '',
});
const educational = reactive<EducationalDraft>(createEducationalDraft());
// Single-line editing buffer for the learning-objectives list (one per line).
const objectivesText = ref('');

// Vocabularies mirror the backend LOMEducational choices; labels come from i18n
// (reuse the existing `lom.*` and `learn.*` keys where possible).
const resourceTypeOptions = [
  'narrative_text', 'image', 'audio', 'video', 'document', 'diagram', 'figure',
  'graph', 'slide', 'table', 'exercise', 'simulation', 'questionnaire', 'exam',
  'experiment', 'problem_statement', 'self_assessment', 'lecture',
];
const difficultyOptions = ['very_easy', 'easy', 'medium', 'difficult', 'very_difficult'];
const contextOptions = ['school', 'higher_education', 'training', 'other'];
const interactivityOptions = ['active', 'expositive', 'mixed'];
const endUserRoleOptions = ['learner', 'teacher', 'author', 'manager'];
const pedagogicalApproachOptions = [
  'expository', 'inquiry', 'constructivist', 'project_based', 'collaborative', 'gamified',
];

const formLocation = ref({ lat: -1.67, lng: -78.65 }); // Helper for map binding

const files = reactive<{ images: File[], audio: File[], video: File[], documents: File[] }>({
  images: [],
  audio: [],
  video: [],
  documents: [],
});

const imagePreviews = ref<string[]>([]);

// Data Sources
const parishes = ref<Parish[]>([]);
const heritageTypes = ref<HeritageType[]>([]);
const heritageCategories = ref<HeritageCategory[]>([]);
const historicalPeriods = ref([
    { value: 'pre-columbian', label: 'Pre-Columbian' },
    { value: 'colonial', label: 'Colonial' },
    { value: 'republican', label: 'Republican' },
    { value: 'contemporary', label: 'Contemporary' },
    { value: 'unknown', label: 'Unknown' },
]);

const loading = ref(false);
const submitting = ref(false);
const step1Error = ref('');
const step1Uploading = ref(false);
const step1UploadProgress = ref<number | null>(null);
const step1UploadXhr = ref<XMLHttpRequest | null>(null);

const narrativeText = ref('');

const aiDraftLoading = ref(false);
const aiDraftError = ref('');
const aiMetaLoading = ref(false);
const aiMetaError = ref('');
const aiMetaNote = ref('');
const aiSuggestedKeywords = ref<string[]>([]);
const aiEduLoading = ref(false);
const aiEduError = ref('');
const aiEduNote = ref('');
const { isAvailable: aiAvailable, refresh: refreshAIAvailability, markUnavailable: markAIUnavailable } = useAIAvailability()

// Map settings
const zoom = ref(13);
const center = ref<[number, number]>([-1.67, -78.65]);

// --- Lifecycle ---
onMounted(async () => {
  loading.value = true;
  try {
    refreshAIAvailability()
    const [parishesRes, typesRes, categoriesRes] = await Promise.all([
      api.get('/parishes/'),
      api.get('/types/'),
      api.get('/categories/all/'),
    ]);
    parishes.value = parishesRes.data.results || parishesRes.data;
    heritageTypes.value = typesRes.data.results || typesRes.data;
    heritageCategories.value = categoriesRes.data.results || categoriesRes.data;

  } catch (error) {
    console.error('Error fetching data:', error);
  } finally {
    loading.value = false;
  }
});

// --- Actions ---
const nextStep = async () => {
  if (submitting.value) return;

  if (currentStep.value === 1) {
    if (step1Uploading.value) return;

    if (resourceType.value === 'text') {
      // Basic check for empty HTML content (strip tags)
      const plainText = narrativeText.value.replace(/<[^>]*>/g, '').trim();
      if (!plainText) return;

      try {
          step1Uploading.value = true;
          step1Error.value = '';
          
          const blob = new Blob([narrativeText.value], { type: 'text/html' });
          const file = new File([blob], "narrative_text.html", { type: 'text/html' });

          const id = await uploadOneFile(file, 'document');
          
          // Store as document
          contribution.documents = [id];
          contribution.images = [];
          contribution.audio = [];
          contribution.video = [];

          currentStep.value = 2;
          return;
      } catch (error) {
        const err = error as any;
        console.error('Error uploading text file:', err);
        step1Error.value = t('contribution.step1.errors.uploadFailed');
        return;
      } finally {
        step1Uploading.value = false;
      }
    }

    const file =
      resourceType.value === 'image' ? files.images[0] :
      resourceType.value === 'audio' ? files.audio[0] :
      resourceType.value === 'video' ? files.video[0] :
      resourceType.value === 'document' ? files.documents[0] :
      undefined;

    if (!file) {
      step1Error.value = t('contribution.step1.errors.selectFile');
      return;
    }

    try {
      step1Uploading.value = true;
      step1UploadProgress.value = 0;
      step1UploadXhr.value = null;
      step1Error.value = '';
      const id = await uploadOneFile(file, resourceType.value);
      contribution.images = resourceType.value === 'image' ? [id] : [];
      contribution.audio = resourceType.value === 'audio' ? [id] : [];
      contribution.video = resourceType.value === 'video' ? [id] : [];
      contribution.documents = resourceType.value === 'document' ? [id] : [];
      currentStep.value = 2;
      return;
    } catch (error) {
      const err = error as any;
      const status = err?.response?.status;
      const data = err?.response?.data;
      console.error('Error uploading file:', err);
      if (status) {
        const detail = typeof data === 'string' ? data : '';
        step1Error.value = `${t('contribution.step1.errors.uploadFailedStatus', { status })} ${detail}`.trim();
      } else {
        step1Error.value = t('contribution.step1.errors.uploadFailed');
      }
      return;
    } finally {
      step1Uploading.value = false;
      step1UploadXhr.value = null;
      step1UploadProgress.value = null;
    }
  }

  step1Error.value = '';
  if (currentStep.value < totalSteps) currentStep.value++;
};

const prevStep = () => {
  if (currentStep.value > 1) currentStep.value--;
};

const setResourceType = (nextType: ContributionResourceType) => {
  resourceType.value = nextType;
  files.images = [];
  files.audio = [];
  files.video = [];
  files.documents = [];
  imagePreviews.value = [];
  step1Error.value = '';
  // narrativeText.value = ''; // Keep text if they switch back and forth? Maybe better to keep it.
  step1UploadProgress.value = null;
  step1UploadXhr.value?.abort();
  step1UploadXhr.value = null;
  contribution.images = [];
  contribution.audio = [];
  contribution.video = [];
  contribution.documents = [];
};

const handleMapClick = (e: any) => {
  formLocation.value = e.latlng;
  contribution.location = { 
    type: 'Point', 
    coordinates: [e.latlng.lng, e.latlng.lat] 
  };
};

const handleFileUpload = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const fileList = target.files;
  if (fileList) {
    const fileType = target.id as 'images' | 'audio' | 'video' | 'documents';
    const firstFile = fileList.item(0);
    if (!firstFile) return;

    if (fileType === 'images') {
      resourceType.value = 'image';
      files.images = [firstFile];
      files.audio = [];
      files.video = [];
      files.documents = [];
      contribution.images = [];
      contribution.audio = [];
      contribution.video = [];
      contribution.documents = [];
    } else if (fileType === 'audio') {
      resourceType.value = 'audio';
      files.images = [];
      files.audio = [firstFile];
      files.video = [];
      files.documents = [];
      contribution.images = [];
      contribution.audio = [];
      contribution.video = [];
      contribution.documents = [];
    } else if (fileType === 'video') {
      resourceType.value = 'video';
      files.images = [];
      files.audio = [];
      files.video = [firstFile];
      files.documents = [];
      contribution.images = [];
      contribution.audio = [];
      contribution.video = [];
      contribution.documents = [];
    } else if (fileType === 'documents') {
      resourceType.value = 'document';
      files.images = [];
      files.audio = [];
      files.video = [];
      files.documents = [firstFile];
      contribution.images = [];
      contribution.audio = [];
      contribution.video = [];
      contribution.documents = [];
    }

    if (fileType === 'images') {
      imagePreviews.value = [];
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target?.result) {
          imagePreviews.value = [e.target.result as string];
        }
      };
      reader.readAsDataURL(firstFile);
    }

    step1Error.value = '';
  }
};

const uploadOneFile = async (file: File, fileType: string) => {
  return await new Promise<string>((resolve, reject) => {
    const token = localStorage.getItem('token');
    const url = `${api.defaults.baseURL}/media/`;
    const xhr = new XMLHttpRequest();
    step1UploadXhr.value = xhr;

    xhr.open('POST', url, true);
    xhr.responseType = 'json';
    xhr.timeout = 600000;

    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    xhr.upload.onprogress = (event) => {
      if (!event.total) return;
      step1UploadProgress.value = Math.round((event.loaded / event.total) * 100);
    };

    let settled = false;
    const finalize = () => {
      if (settled) return;
      if (xhr.readyState !== XMLHttpRequest.DONE) return;
      settled = true;

      const status = xhr.status;
      const data =
        xhr.response ??
        (() => {
          if (xhr.responseType === '' || xhr.responseType === 'text') {
            try {
              return xhr.responseText ? JSON.parse(xhr.responseText) : xhr.responseText;
            } catch {
              return xhr.responseText;
            }
          }
          return null;
        })();

      if (status >= 200 && status < 300) {
        const id = (data as any)?.id;
        if (typeof id === 'string' && id.length) {
          resolve(id);
        } else {
          reject({ response: { status, data } });
        }
        return;
      }

      reject({ response: { status, data } });
    };

    xhr.onload = finalize;
    xhr.onreadystatechange = finalize;
    xhr.onerror = () => {
      if (settled) return;
      settled = true;
      reject({ message: 'Network error' });
    };
    xhr.ontimeout = () => {
      if (settled) return;
      settled = true;
      reject({ message: 'Upload timed out' });
    };
    xhr.onabort = () => {
      if (settled) return;
      settled = true;
      reject({ code: 'ERR_CANCELED' });
    };

    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);
    xhr.send(formData);
  });
};

// True only when a service worker controls this page AND the API shares the
// page's origin — the two conditions under which the SW can intercept the
// contribution POST and queue it for background sync.
const canServiceWorkerQueueContribution = (): boolean => {
  if (typeof navigator === 'undefined' || !navigator.serviceWorker?.controller) return false;
  const base = api.defaults?.baseURL || import.meta.env.VITE_API_BASE_URL || '';
  try {
    // Relative base (e.g. "/api/v1") resolves against the page origin → same-origin.
    return new URL(base, window.location.origin).origin === window.location.origin;
  } catch {
    return false;
  }
};

// Build the educational sub-payload, dropping empty values so the backend only
// receives fields the contributor actually set (avoids failing enum validation
// on blank strings and keeps the LOM "to be completed" where left empty).
const buildEducationalPayload = (): Record<string, any> | null => {
  syncObjectivesFromText();
  const out: Record<string, any> = {};
  (Object.keys(educational) as (keyof EducationalDraft)[]).forEach((key) => {
    const value = educational[key];
    if (Array.isArray(value)) {
      if (value.length) out[key] = value;
    } else if (typeof value === 'string' && value.trim()) {
      out[key] = value;
    }
  });
  return Object.keys(out).length ? out : null;
};

const submitContribution = async () => {
  submitting.value = true;
  try {
    // Submit data (resource is uploaded in step 1 if provided). The educational
    // layer, when filled, rides along under `educational`.
    const payload: Record<string, any> = { ...contribution };
    const edu = buildEducationalPayload();
    if (edu) payload.educational = edu;
    await api.post('/contributions/', payload);

    queuedOffline.value = false;
    submittedSuccess.value = true;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (error) {
    console.error('Error submitting contribution:', error);

    // The service worker only enqueues the POST for background sync if it is
    // actually controlling this page AND the API is same-origin (a SW only
    // intercepts requests within its own origin). Only then can we honestly
    // tell the user the submission is queued; otherwise the POST is lost and we
    // must surface a real error instead of a false success.
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
    if (offline && canServiceWorkerQueueContribution()) {
      queuedOffline.value = true;
      submittedSuccess.value = true;
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    alert(t('contribution.actions.error'));
  } finally {
    submitting.value = false;
  }
};

// Map an AI request error to a localized message in the given ref (503 →
// unavailable + mark the service down, 429 → rate-limited, else → generic).
const applyAIError = (err: any, target: { value: string }) => {
  const status = err?.response?.status;
  if (status === 503) {
    target.value = t('ai.unavailable');
    markAIUnavailable();
  } else if (status === 429) {
    target.value = t('ai.rateLimited');
  } else {
    target.value = t('ai.genericError');
  }
};

const generateAIDraft = async () => {
  if (aiDraftLoading.value || submitting.value) return;
  aiDraftError.value = '';
  try {
    aiDraftLoading.value = true;
    const res = await aiService.contributionDraft({
      language: String(locale.value || 'es'),
      title: String(contribution.title || ''),
      description: String(contribution.description || ''),
    });
    if (typeof res.title === 'string') contribution.title = res.title;
    if (typeof res.description === 'string') contribution.description = res.description;
  } catch (err: any) {
    applyAIError(err, aiDraftError);
  } finally {
    aiDraftLoading.value = false;
  }
};

const generateAIMetadata = async () => {
  if (aiMetaLoading.value || submitting.value) return;
  aiMetaError.value = '';
  aiMetaNote.value = '';
  aiSuggestedKeywords.value = [];
  try {
    aiMetaLoading.value = true;
    const res = await aiService.contributionMetadata({
      language: String(locale.value || 'es'),
      title: String(contribution.title || ''),
      description: String(contribution.description || ''),
      address: String(contribution.address || ''),
    });

    let appliedField = false;
    // Apply the historical period only if it matches a known option.
    if (res.historical_period && historicalPeriods.value.some(p => p.value === res.historical_period)) {
      contribution.historical_period = res.historical_period;
      appliedField = true;
    }
    if (res.external_registry_url && !contribution.external_registry_url) {
      contribution.external_registry_url = res.external_registry_url;
      appliedField = true;
    }
    // Keywords belong to the LOM educational layer (added in a later phase),
    // so surface them as a suggestion rather than silently dropping them.
    aiSuggestedKeywords.value = Array.isArray(res.keywords) ? res.keywords : [];

    // Report honestly what happened: a field was filled, only keywords were
    // suggested, or nothing usable came back.
    if (appliedField) {
      aiMetaNote.value = t('ai.metadataApplied');
    } else if (aiSuggestedKeywords.value.length) {
      aiMetaNote.value = t('ai.metadataKeywordsOnly');
    } else {
      aiMetaNote.value = t('ai.metadataNothing');
    }
  } catch (err: any) {
    aiSuggestedKeywords.value = [];
    applyAIError(err, aiMetaError);
  } finally {
    aiMetaLoading.value = false;
  }
};

// Keep the objectives text buffer and the structured list in sync (one per line).
const syncObjectivesFromText = () => {
  educational.learning_objectives = objectivesText.value
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
};

// Best-effort resource type derived from the chosen upload, so the AI has a hint.
const inferredResourceType = (): string => {
  if (resourceType.value === 'image') return 'image';
  if (resourceType.value === 'audio') return 'audio';
  if (resourceType.value === 'video') return 'video';
  if (resourceType.value === 'document') return 'document';
  return 'narrative_text';
};

const generateAIEducational = async () => {
  if (aiEduLoading.value || submitting.value) return;
  aiEduError.value = '';
  aiEduNote.value = '';
  try {
    aiEduLoading.value = true;
    const res = await aiService.educationalMetadata({
      language: String(locale.value || 'es'),
      title: String(contribution.title || ''),
      description: String(contribution.description || ''),
      resource_type: educational.learning_resource_type || inferredResourceType(),
    });

    // Only apply values that match a known vocabulary option; free-text/age/time
    // pass through as-is. Objectives replace the current list.
    const applyEnum = (key: keyof EducationalDraft, value: string | null | undefined, allowed: string[]) => {
      if (value && allowed.includes(value)) (educational as any)[key] = value;
    };
    applyEnum('learning_resource_type', res.learning_resource_type, resourceTypeOptions);
    applyEnum('difficulty', res.difficulty, difficultyOptions);
    applyEnum('context', res.context, contextOptions);
    if (res.typical_age_range) educational.typical_age_range = res.typical_age_range;
    if (res.typical_learning_time) educational.typical_learning_time = res.typical_learning_time;
    if (Array.isArray(res.learning_objectives) && res.learning_objectives.length) {
      educational.learning_objectives = res.learning_objectives;
      objectivesText.value = res.learning_objectives.join('\n');
    }
    if (Array.isArray(res.keywords) && res.keywords.length) {
      // Surface keywords as a suggestion for the general layer.
      aiSuggestedKeywords.value = res.keywords;
    }
    aiEduNote.value = t('ai.educationalApplied');
  } catch (err: any) {
    applyAIError(err, aiEduError);
  } finally {
    aiEduLoading.value = false;
  }
};

const resetForm = () => {
  submittedSuccess.value = false;
  queuedOffline.value = false;
  currentStep.value = 1;
  setResourceType('text');
  
  contribution.title = '';
  contribution.description = '';
  contribution.location = { type: 'Point', coordinates: [-78.65, -1.67] };
  contribution.address = '';
  contribution.parish = null;
  contribution.heritage_type = null;
  contribution.heritage_category = null;
  contribution.historical_period = '';
  contribution.external_registry_url = '';
  contribution.images = [];
  contribution.audio = [];
  contribution.video = [];
  contribution.documents = [];
  
  formLocation.value = { lat: -1.67, lng: -78.65 };

  aiDraftLoading.value = false;
  aiDraftError.value = '';
  narrativeText.value = '';

  Object.assign(educational, createEducationalDraft());
  objectivesText.value = '';
  aiEduLoading.value = false;
  aiEduError.value = '';
  aiEduNote.value = '';
  aiSuggestedKeywords.value = [];
};

// --- Computed ---
const isStepValid = computed(() => {
  switch (currentStep.value) {
    case 1: // Resource
      if (resourceType.value === 'text') {
         const plainText = narrativeText.value.replace(/<[^>]*>/g, '').trim();
         return plainText.length > 0;
      }
      if (resourceType.value === 'image') return (contribution.images?.length || files.images.length > 0) ? true : false;
      if (resourceType.value === 'audio') return (contribution.audio?.length || files.audio.length > 0) ? true : false;
      if (resourceType.value === 'video') return (contribution.video?.length || files.video.length > 0) ? true : false;
      if (resourceType.value === 'document') return (contribution.documents?.length || files.documents.length > 0) ? true : false;
      return false;
    case 2: // General
      return contribution.title && contribution.description && contribution.heritage_type && contribution.heritage_category;
    case 3: // Location
      return contribution.parish; // Location is defaulted, address optional
    case 4: // Details
      return true; // Optional mostly
    case 5: // Educational layer
      return true; // Entirely optional; can be completed later or via the LOM editor
    case 6: // Review
      return true;
    default:
      return false;
  }
});
</script>

<template>
  <div class="bg-white rounded-xl shadow-lg overflow-hidden">
    <!-- Success Message View -->
    <div v-if="submittedSuccess" class="p-12 text-center animate-fade-in">
      <div class="mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-green-100 mb-6">
        <svg class="h-10 w-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
        </svg>
      </div>
      <h2 class="text-3xl font-bold text-gray-900 mb-4">{{ t('contribution.successPage.title') }}</h2>
      <p class="text-lg text-gray-600 mb-10 max-w-2xl mx-auto">
        {{ t('contribution.successPage.message') }}
      </p>
      <p v-if="queuedOffline" class="text-sm text-gray-700 mb-10 max-w-2xl mx-auto">
        {{ t('contribution.successPage.offlineQueued') }}
      </p>
      <div class="flex flex-col sm:flex-row justify-center space-y-4 sm:space-y-0 sm:space-x-4">
        <button 
          @click="resetForm"
          class="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-bold transition shadow-lg"
        >
          {{ t('contribution.successPage.submitAnother') }}
        </button>
        <button 
          @click="router.push('/')"
          class="px-6 py-3 border border-gray-300 text-gray-700 bg-white rounded-lg hover:bg-gray-50 font-bold transition"
        >
          {{ t('contribution.successPage.goHome') }}
        </button>
      </div>
    </div>

    <!-- Main Contribution Form -->
    <div v-else>
      <!-- Stepper Header -->
      <div class="bg-gray-50 border-b border-gray-200 px-6 py-4">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-gray-500">{{ t('contribution.progress', { current: currentStep, total: totalSteps }) }}</span>
        <div class="flex space-x-2">
          <div v-for="step in totalSteps" :key="step" 
               class="h-2 w-10 rounded-full transition-colors duration-300"
               :class="step <= currentStep ? 'bg-indigo-600' : 'bg-gray-200'"></div>
        </div>
      </div>
      <h2 class="text-xl font-bold text-gray-900 mt-2">
        <span v-if="currentStep === 1">{{ t('contribution.steps.1') }}</span>
        <span v-if="currentStep === 2">{{ t('contribution.steps.2') }}</span>
        <span v-if="currentStep === 3">{{ t('contribution.steps.3') }}</span>
        <span v-if="currentStep === 4">{{ t('contribution.steps.4') }}</span>
        <span v-if="currentStep === 5">{{ t('contribution.steps.5') }}</span>
        <span v-if="currentStep === 6">{{ t('contribution.steps.6') }}</span>
      </h2>
    </div>

    <!-- Form Content -->
    <div class="p-8">
      <form @submit.prevent>
        
	        <!-- Step 1: Resource -->
	        <div v-if="currentStep === 1" class="space-y-6">
          <div v-if="step1Uploading" class="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
            <div class="flex items-center">
              <BaseSpinner class="h-5 w-5 text-indigo-600 mr-3" />
              <div class="text-sm font-medium text-indigo-900">{{ t('contribution.step1.uploading') }}</div>
            </div>
            <div class="text-xs text-indigo-800 mt-1">
              <span v-if="step1UploadProgress !== null">{{ step1UploadProgress }}%</span>
              <span v-else>{{ t('contribution.step1.uploadingWait') }}</span>
            </div>
            <div v-if="step1UploadProgress !== null" class="mt-2 h-2 w-full rounded-full bg-indigo-200 overflow-hidden">
              <div class="h-full bg-indigo-600 transition-all" :style="{ width: `${step1UploadProgress}%` }"></div>
            </div>
            <div class="mt-3">
              <button
                type="button"
                class="text-xs font-medium text-indigo-900 underline"
                @click="step1UploadXhr?.abort()"
              >
                {{ t('contribution.step1.cancelUpload') }}
              </button>
            </div>
          </div>

	          <div class="bg-blue-50 p-4 rounded-lg text-blue-800 text-sm">
	            {{ t('contribution.step1.instruction') }}
	          </div>

	          <div>
	            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.resourceType') }}</label>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
	              <button
	                type="button"
	                @click="setResourceType('image')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'image' ? 'border-indigo-600 bg-indigo-50 text-indigo-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.image') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.imageDesc') }}</div>
              </button>
	              <button
	                type="button"
	                @click="setResourceType('audio')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'audio' ? 'border-indigo-600 bg-indigo-50 text-indigo-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.audio') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.audioDesc') }}</div>
              </button>
	              <button
	                type="button"
	                @click="setResourceType('video')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'video' ? 'border-indigo-600 bg-indigo-50 text-indigo-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.video') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.videoDesc') }}</div>
              </button>
	              <button
	                type="button"
	                @click="setResourceType('document')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'document' ? 'border-indigo-600 bg-indigo-50 text-indigo-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.document') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.documentDesc') }}</div>
              </button>
	              <button
	                type="button"
	                @click="setResourceType('text')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'text' ? 'border-indigo-600 bg-indigo-50 text-indigo-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.text') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.textDesc') }}</div>
              </button>
            </div>
	          </div>

          <div v-if="step1Error" class="rounded-md bg-red-50 p-4 text-sm text-red-700">
            {{ step1Error }}
          </div>

	          <div v-if="resourceType === 'image'">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.uploadLabel', { type: t('contribution.step1.types.image') }) }}</label>
            <div class="flex items-center justify-center w-full">
              <label
                for="images"
                class="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100"
              >
                <div class="flex flex-col items-center justify-center pt-5 pb-6">
                  <svg class="w-8 h-8 mb-4 text-gray-500" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 16">
                    <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L8 8m2-2 2 2"/>
                  </svg>
                  <p class="text-sm text-gray-500"><span class="font-semibold">{{ t('contribution.step1.clickToUpload') }}</span></p>
                </div>
	                <input id="images" type="file" class="hidden" accept="image/*" @change="handleFileUpload" />
	              </label>
	            </div>

            <div v-if="imagePreviews.length" class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <div class="relative group aspect-square bg-gray-100 rounded-lg overflow-hidden">
                <img :src="imagePreviews[0]" class="w-full h-full object-cover" />
              </div>
            </div>
          </div>

	          <div v-else-if="resourceType === 'audio'">
	            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.uploadLabel', { type: t('contribution.step1.types.audio') }) }}</label>
	            <input id="audio" type="file" accept="audio/*" :disabled="step1Uploading || submitting" class="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none disabled:opacity-50" @change="handleFileUpload">
	            <p v-if="files.audio.length" class="text-xs text-gray-600 mt-1">{{ t('contribution.step1.selected', { name: files.audio[0]?.name }) }}</p>
	          </div>

	          <div v-else-if="resourceType === 'video'">
	            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.uploadLabel', { type: t('contribution.step1.types.video') }) }}</label>
	            <input id="video" type="file" accept="video/*" :disabled="step1Uploading || submitting" class="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none disabled:opacity-50" @change="handleFileUpload">
	            <p v-if="files.video.length" class="text-xs text-gray-600 mt-1">{{ t('contribution.step1.selected', { name: files.video[0]?.name }) }}</p>
	          </div>

	          <div v-else-if="resourceType === 'document'">
	            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.uploadLabel', { type: t('contribution.step1.types.document') }) }}</label>
	            <input id="documents" type="file" accept="application/pdf" :disabled="step1Uploading || submitting" class="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none disabled:opacity-50" @change="handleFileUpload">
	            <p v-if="files.documents.length" class="text-xs text-gray-600 mt-1">{{ t('contribution.step1.selected', { name: files.documents[0]?.name }) }}</p>
	          </div>

          <div v-else class="space-y-2">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.types.text') }}</label>
            <div class="relative bg-white rich-text-container">
              <QuillEditor 
                v-model:content="narrativeText" 
                contentType="html"
                theme="snow"
                :readOnly="step1Uploading || submitting"
                style="height: 300px"
              />
            </div>
          </div>
        </div>

        <!-- Step 2: General Information -->
        <div v-if="currentStep === 2" class="space-y-6">
          <AiActionButton
            :label="t('ai.draftButton')"
            :loading-label="t('ai.generating')"
            :loading="aiDraftLoading"
            :available="aiAvailable"
            :disabled="submitting"
            :error="aiDraftError"
            @click="generateAIDraft"
          />

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step2.fields.title') }} <span class="text-red-500">*</span></label>
            <input v-model="contribution.title" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step2.fields.placeholders.title')" required />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step2.fields.description') }} <span class="text-red-500">*</span></label>
            <textarea v-model="contribution.description" rows="4" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step2.fields.placeholders.description')" required></textarea>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step2.fields.heritageType') }} <span class="text-red-500">*</span></label>
              <select v-model="contribution.heritage_type" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                <option :value="null" disabled>{{ t('contribution.step2.fields.selectType') }}</option>
                <option v-for="t in heritageTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step2.fields.category') }} <span class="text-red-500">*</span></label>
              <select v-model="contribution.heritage_category" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                <option :value="null" disabled>{{ t('contribution.step2.fields.selectCategory') }}</option>
                <option v-for="c in heritageCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Step 3: Location -->
        <div v-if="currentStep === 3" class="space-y-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step3.fields.parish') }} <span class="text-red-500">*</span></label>
            <select v-model="contribution.parish" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
              <option :value="null" disabled>{{ t('contribution.step3.fields.selectParish') }}</option>
              <option v-for="p in parishes" :key="p.id" :value="p.id">{{ p.name }} ({{ p.canton }})</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step3.fields.address') }}</label>
            <input v-model="contribution.address" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step3.fields.addressPlaceholder')" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step3.fields.pinLocation') }} <span class="text-red-500">*</span></label>
            <div class="h-80 rounded-lg overflow-hidden border border-gray-300">
              <l-map ref="map" v-model:zoom="zoom" :center="center" @click="handleMapClick">
                <l-tile-layer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                              layer-type="base" name="OpenStreetMap"></l-tile-layer>
                <l-marker :lat-lng="[formLocation.lat, formLocation.lng] as [number, number]"></l-marker>
              </l-map>
            </div>
            <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step3.fields.coordinates', { lat: formLocation.lat.toFixed(5), lng: formLocation.lng.toFixed(5) }) }}</p>
          </div>
        </div>

        <!-- Step 4: Details -->
        <div v-if="currentStep === 4" class="space-y-6">
          <AiActionButton
            :label="t('ai.metadataButton')"
            :loading-label="t('ai.metadataGenerating')"
            :loading="aiMetaLoading"
            :available="aiAvailable"
            :disabled="submitting"
            :error="aiMetaError"
            @click="generateAIMetadata"
          />

          <p v-if="aiMetaNote" class="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-2 rounded-lg">
            {{ aiMetaNote }}
          </p>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step4.fields.historicalPeriod') }}</label>
            <select v-model="contribution.historical_period" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
              <option value="" disabled>{{ t('contribution.step4.fields.selectPeriod') }}</option>
              <option v-for="p in historicalPeriods" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step4.fields.externalUrl') }}</label>
            <input v-model="contribution.external_registry_url" type="url" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step4.fields.urlPlaceholder')" />
          </div>

          <div v-if="aiSuggestedKeywords.length" class="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p class="text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step4.fields.suggestedKeywords') }}</p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="kw in aiSuggestedKeywords"
                :key="kw"
                class="inline-block px-2 py-1 text-xs rounded-full bg-indigo-100 text-indigo-800"
              >{{ kw }}</span>
            </div>
          </div>
        </div>

        <!-- Step 5: Educational layer (IEEE-LOM) -->
        <div v-if="currentStep === 5" class="space-y-6">
          <div class="bg-blue-50 p-4 rounded-lg text-blue-800 text-sm">
            {{ t('contribution.step5edu.instruction') }}
          </div>

          <AiActionButton
            :label="t('ai.educationalButton')"
            :loading-label="t('ai.educationalGenerating')"
            :loading="aiEduLoading"
            :available="aiAvailable"
            :disabled="submitting"
            :error="aiEduError"
            @click="generateAIEducational"
          />

          <p v-if="aiEduNote" class="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-2 rounded-lg">
            {{ aiEduNote }}
          </p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.resourceType') }}</label>
              <select v-model="educational.learning_resource_type" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                <option value="">{{ t('contribution.step5edu.unset') }}</option>
                <option v-for="opt in resourceTypeOptions" :key="opt" :value="opt">{{ t(`lom.resource_type.${opt}`, opt) }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.difficulty') }}</label>
              <select v-model="educational.difficulty" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                <option value="">{{ t('contribution.step5edu.unset') }}</option>
                <option v-for="opt in difficultyOptions" :key="opt" :value="opt">{{ t(`lom.difficulty.${opt}`, opt) }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.context') }}</label>
              <select v-model="educational.context" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                <option value="">{{ t('contribution.step5edu.unset') }}</option>
                <option v-for="opt in contextOptions" :key="opt" :value="opt">{{ t(`lom.context.${opt}`, opt) }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.ageRange') }}</label>
              <input v-model="educational.typical_age_range" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step5edu.placeholders.ageRange')" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.learningTime') }}</label>
              <input v-model="educational.typical_learning_time" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step5edu.placeholders.learningTime')" />
              <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step5edu.help.learningTime') }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.interactivity') }}</label>
              <select v-model="educational.interactivity_type" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                <option value="">{{ t('contribution.step5edu.unset') }}</option>
                <option v-for="opt in interactivityOptions" :key="opt" :value="opt">{{ t(`lom.interactivity.${opt}`, opt) }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.audience') }}</label>
              <select v-model="educational.intended_end_user_role" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                <option value="">{{ t('contribution.step5edu.unset') }}</option>
                <option v-for="opt in endUserRoleOptions" :key="opt" :value="opt">{{ t(`lom.audience.${opt}`, opt) }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.approach') }}</label>
              <select v-model="educational.pedagogical_approach" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                <option value="">{{ t('contribution.step5edu.unset') }}</option>
                <option v-for="opt in pedagogicalApproachOptions" :key="opt" :value="opt">{{ t(`lom.approach.${opt}`, opt) }}</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.objectives') }}</label>
            <textarea v-model="objectivesText" @blur="syncObjectivesFromText" rows="4" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step5edu.placeholders.objectives')"></textarea>
            <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step5edu.help.objectives') }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.prerequisites') }}</label>
            <textarea v-model="educational.prerequisites" rows="2" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step5edu.placeholders.prerequisites')"></textarea>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.competencies') }}</label>
            <textarea v-model="educational.competencies" rows="2" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" :placeholder="t('contribution.step5edu.placeholders.competencies')"></textarea>
          </div>
        </div>

        <!-- Step 6: Review -->
        <div v-if="currentStep === 6" class="space-y-6">
          <div class="bg-gray-50 p-6 rounded-lg">
            <h3 class="text-lg font-bold text-gray-900 mb-4">{{ t('contribution.step5.summary') }}</h3>
            <dl class="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
              <div class="sm:col-span-1">
                <dt class="text-sm font-medium text-gray-500">{{ t('contribution.step2.fields.title') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">{{ contribution.title }}</dd>
              </div>
              <div class="sm:col-span-1">
                <dt class="text-sm font-medium text-gray-500">{{ t('contribution.step2.fields.heritageType') }} / {{ t('contribution.step2.fields.category') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">
                  {{ heritageTypes.find(t => t.id === contribution.heritage_type)?.name }} / 
                  {{ heritageCategories.find(c => c.id === contribution.heritage_category)?.name }}
                </dd>
              </div>
              <div class="sm:col-span-2">
                <dt class="text-sm font-medium text-gray-500">{{ t('contribution.step2.fields.description') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">{{ contribution.description }}</dd>
              </div>
              <div class="sm:col-span-1">
                <dt class="text-sm font-medium text-gray-500">{{ t('contribution.step3.fields.parish') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">{{ parishes.find(p => p.id === contribution.parish)?.name }}</dd>
              </div>
              <div class="sm:col-span-1">
                <dt class="text-sm font-medium text-gray-500">{{ t('contribution.step3.fields.pinLocation') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">{{ formLocation.lat.toFixed(4) }}, {{ formLocation.lng.toFixed(4) }}</dd>
              </div>
              <div class="sm:col-span-1">
                <dt class="text-sm font-medium text-gray-500">{{ t('contribution.step5.media') }}</dt>
	                <dd class="mt-1 text-sm text-gray-900">
	                   <span v-if="resourceType === 'text'">{{ t('contribution.step1.types.text') }}</span>
	                   <span v-else-if="resourceType === 'image' && files.images.length">{{ t('contribution.step1.types.image') }}: {{ files.images[0]?.name }}</span>
	                   <span v-else-if="resourceType === 'audio' && files.audio.length">{{ t('contribution.step1.types.audio') }}: {{ files.audio[0]?.name }}</span>
	                   <span v-else-if="resourceType === 'video' && files.video.length">{{ t('contribution.step1.types.video') }}: {{ files.video[0]?.name }}</span>
	                   <span v-else-if="resourceType === 'document' && files.documents.length">{{ t('contribution.step1.types.document') }}: {{ files.documents[0]?.name }}</span>
	                   <span v-else>{{ t('contribution.step5.none') }}</span>
	                </dd>
              </div>
            </dl>
          </div>
        </div>

	        <!-- Navigation Buttons -->
	        <div class="mt-8 flex justify-between pt-6 border-t border-gray-200">
          <button 
            type="button" 
            @click="prevStep" 
            :disabled="currentStep === 1 || submitting"
            class="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
            :class="{'invisible': currentStep === 1}"
          >
            {{ t('contribution.actions.back') }}
          </button>
          
	          <button 
	            v-if="currentStep < totalSteps"
	            type="button" 
	            @click="nextStep" 
	            :disabled="submitting || step1Uploading || (currentStep !== 1 && !isStepValid)"
	            class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition shadow-sm"
	          >
	            {{ t('contribution.actions.next') }}
	          </button>
          
          <button 
            v-else
            type="button" 
            @click="submitContribution" 
            :disabled="submitting"
            class="px-8 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-bold transition shadow-md flex items-center"
          >
            <BaseSpinner v-if="submitting" class="-ml-1 mr-3 h-5 w-5 text-white" />
            {{ submitting ? t('contribution.actions.submitting') : t('contribution.actions.submit') }}
          </button>
        </div>
      </form>
    </div>
    </div>
  </div>
</template>

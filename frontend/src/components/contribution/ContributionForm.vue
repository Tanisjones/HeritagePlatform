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
import { useCityStore } from '@/stores/city';
import { useCityPath } from '@/composables/useCityPath';
import type { HeritageItem, HeritageItemContribution, Parish, HeritageType, HeritageCategory } from '@/types/heritage';
import api, { aiService } from '@/services/api';
import { useAIAvailability } from '@/services/aiAvailability'
import { useAiError } from '@/composables/useAiError';
import { useDurationValidation } from '@/composables/useDurationValidation';
import { useGeolocation } from '@/composables/useGeolocation';
import { useToast } from '@/composables/useDialogs';
import { useFileUpload } from '@/composables/useFileUpload';
import { LOM_RESOURCE_TYPES, LOM_DIFFICULTIES, LOM_CONTEXTS } from '@/constants/lomVocab';
import AiActionButton from '@/components/common/AiActionButton.vue';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import LocationPickerMap from '@/components/map/LocationPickerMap.vue';
import ContributionEducationStep, { type EducationalDraft } from '@/components/contribution/ContributionEducationStep.vue';
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

// --- State ---
const { t, locale } = useI18n();
const router = useRouter();
const { cityPath } = useCityPath();
const toast = useToast();
const emit = defineEmits(['step-change']);

const currentStep = ref(1);

watch(currentStep, (newStep) => {
  emit('step-change', newStep);
});

const totalSteps = 6;
const submittedSuccess = ref(false);
const queuedOffline = ref(false);

// B2 — compact single-page mode for experienced contributors: every section is
// visible at once and the resource uploads at submit time instead of on step 1.
// The preference sticks across visits.
const COMPACT_STORAGE_KEY = 'hp_contrib_compact';
const compactMode = ref(localStorage.getItem(COMPACT_STORAGE_KEY) === '1');
watch(compactMode, (v) => localStorage.setItem(COMPACT_STORAGE_KEY, v ? '1' : '0'));
// Sections 1-5 all show in compact mode; the review step is wizard-only (the
// whole form already being on screen IS the review).
const showSection = (n: number) => (compactMode.value ? n <= 5 : currentStep.value === n);

// B2 — save-as-draft state. A draft needs the step-2 basics (see draftValid);
// the resource and everything else can come later via "Mis contribuciones".
const savingDraft = ref(false);
const draftSaved = ref(false);

type ContributionResourceType = 'image' | 'audio' | 'video' | 'document' | 'text';
const resourceType = ref<ContributionResourceType>('text');

const cityStore = useCityStore();
// Default new-contribution point: the active city's center (Riobamba fallback).
const cityDefaultLngLat = (): [number, number] => {
  const c = cityStore.activeCity?.center?.coordinates;
  return Array.isArray(c) ? [c[0], c[1]] : [-78.65, -1.67];
};
const cityDefaultLatLng = () => {
  const [lng, lat] = cityDefaultLngLat();
  return { lat, lng };
};

const contribution = reactive<Partial<HeritageItemContribution>>({
  title: '',
  description: '',
  location: { type: 'Point', coordinates: cityDefaultLngLat() }, // Default to the active city
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
  tags: [],
});

// B1 — free-form tags chip editor (step 4). AI-suggested keywords become
// clickable "add as tag" chips instead of display-only text.
const MAX_TAGS = 10;
const tagInput = ref('');
const addTag = (raw?: string) => {
  const name = String(raw ?? tagInput.value).replace(/,/g, ' ').trim().replace(/\s+/g, ' ');
  if (!name) return;
  const tags = contribution.tags ?? (contribution.tags = []);
  if (tags.length >= MAX_TAGS) return;
  if (!tags.some((t) => t.toLowerCase() === name.toLowerCase())) tags.push(name.slice(0, 50));
  tagInput.value = '';
};
const removeTag = (index: number) => contribution.tags?.splice(index, 1);

// B7 — free-text category suggestion, relayed to the city's curators.
const showSuggestCategory = ref(false);
const suggestedCategory = ref('');

// --- Educational (IEEE-LOM §5) layer captured in step 5 ---
// The educational draft shape lives with the step component (single source of
// truth). Sent to the backend under `educational` on the contribution POST; the
// API validates it through LOMEducationalSerializer. All fields optional —
// blanks are stripped before submit.
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

// Client-side ISO-8601 guard for learning time (shared with the LOM editor),
// so a bad value is caught here instead of failing the whole submit server-side.
const eduTimeError = useDurationValidation(
  () => educational.typical_learning_time,
  { invalidKey: 'contribution.step5edu.errors.duration', monthsKey: 'contribution.step5edu.errors.months' },
);

// Vocabularies the AI-metadata mapping validates against (the full option lists
// for the selects now live in ContributionEducationStep).
const resourceTypeOptions = LOM_RESOURCE_TYPES;
const difficultyOptions = LOM_DIFFICULTIES;
const contextOptions = LOM_CONTEXTS;

const formLocation = ref(cityDefaultLatLng()); // Helper for map binding

// On a direct page load the city catalog resolves AFTER this component seeds
// its default pin, so the fallback coordinates would stick. Re-seed once the
// active city arrives — but only while the pin still sits on a seeded default
// (never clobber a location the user already picked on the map).
watch(() => cityStore.activeCity, (city, previous) => {
  if (!city) return;
  const seeded = [
    { lat: -1.67, lng: -78.65 }, // hardcoded fallback
    ...(previous?.center?.coordinates
      ? [{ lat: previous.center.coordinates[1], lng: previous.center.coordinates[0] }]
      : []),
  ];
  const current = formLocation.value;
  const untouched = seeded.some(p => p.lat === current.lat && p.lng === current.lng);
  if (untouched) {
    contribution.location = { type: 'Point', coordinates: cityDefaultLngLat() };
    formLocation.value = cityDefaultLatLng();
  }
});

const files = reactive<{ images: File[], audio: File[], video: File[], documents: File[] }>({
  images: [],
  audio: [],
  video: [],
  documents: [],
});

const imagePreviews = ref<string[]>([]);

// B4 — client-side size guard; mirrors the deployment's nginx client_max_body_size.
const MAX_UPLOAD_MB = 100;

// B5 — "usar mi ubicación": one-shot fix from the shared geolocation composable.
const { isSupported: geoSupported, getCurrent: getCurrentPosition } = useGeolocation();
const locating = ref(false);
const useMyLocation = async () => {
  if (locating.value) return;
  locating.value = true;
  try {
    const [lng, lat] = await getCurrentPosition();
    onLocationUpdate([lat, lng]);
  } catch {
    toast.error(t('contribution.step3.geolocationError'));
  } finally {
    locating.value = false;
  }
};

// B4 — near-duplicate warning. Debounced, best-effort lookups against the
// existing search + nearby endpoints; never blocks the wizard. The nearby leg
// only runs once the user has actually moved the pin — the seeded city-center
// default would otherwise "match" everything downtown.
const possibleDuplicates = ref<HeritageItem[]>([]);
const duplicatesDismissed = ref(false);
const pinTouched = ref(false);
let duplicateTimer: ReturnType<typeof setTimeout> | null = null;

const checkDuplicates = async () => {
  if (duplicatesDismissed.value || submittedSuccess.value) return;
  const title = (contribution.title || '').trim();
  const byTitle = title.length >= 4;
  if (!byTitle && !pinTouched.value) {
    possibleDuplicates.value = [];
    return;
  }
  try {
    const [titleRes, nearbyRes] = await Promise.all([
      byTitle
        ? api.get('/heritage-items/', { params: { search: title, page_size: 5 } })
        : Promise.resolve(null),
      pinTouched.value
        ? api.get('/heritage-items/nearby/', {
            params: {
              latitude: formLocation.value.lat,
              longitude: formLocation.value.lng,
              radius: 0.3,
            },
          })
        : Promise.resolve(null),
    ]);
    const seen = new Set<string>();
    const merged: HeritageItem[] = [];
    for (const res of [titleRes, nearbyRes]) {
      const list: HeritageItem[] = res ? (res.data?.results ?? res.data ?? []) : [];
      for (const item of list) {
        if (item?.id && !seen.has(item.id)) {
          seen.add(item.id);
          merged.push(item);
        }
      }
    }
    possibleDuplicates.value = merged.slice(0, 3);
  } catch {
    // Best-effort: a failed lookup must never get in the way of contributing.
  }
};
const scheduleDuplicateCheck = () => {
  if (duplicateTimer) clearTimeout(duplicateTimer);
  duplicateTimer = setTimeout(checkDuplicates, 700);
};
watch(() => contribution.title, scheduleDuplicateCheck);
// Pin moves re-run the lookup too (formLocation is declared above this block).
watch(formLocation, scheduleDuplicateCheck);

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
// Shared XHR uploader (progress + abort) — replaces the hand-rolled XHR that
// used to live in this component. Aliased to the existing template names.
const {
  uploading: step1Uploading,
  progress: step1UploadProgress,
  uploadFile: uploadOneFile,
  abort: abortUpload,
} = useFileUpload();

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
const { isAvailable: aiAvailable, refresh: refreshAIAvailability } = useAIAvailability()

// Map settings
const zoom = ref(13);

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

// The staged (not yet uploaded) file for the current resource type.
const stagedFile = (): File | undefined =>
  resourceType.value === 'image' ? files.images[0] :
  resourceType.value === 'audio' ? files.audio[0] :
  resourceType.value === 'video' ? files.video[0] :
  resourceType.value === 'document' ? files.documents[0] :
  undefined;

// Identity of the staged resource. Compact mode calls ensureResourceUploaded on
// every submit attempt, so this is what makes re-submits (and wizard back/next)
// skip re-uploading an unchanged resource. Empty string = nothing staged.
const stagedSignature = (): string => {
  if (resourceType.value === 'text') {
    const plain = narrativeText.value.replace(/<[^>]*>/g, '').trim();
    return plain ? `text:${narrativeText.value}` : '';
  }
  const file = stagedFile();
  return file ? `${resourceType.value}:${file.name}:${file.size}:${file.lastModified}` : '';
};

const uploadedSignature = ref('');

/**
 * Upload the staged resource (file or narrative text) unless it's already up.
 * With required=false (drafts) an empty step 1 passes through — the resource
 * can be added later from "Mis contribuciones". Returns false, with
 * step1Error set, when a required resource is missing or the upload fails.
 */
const ensureResourceUploaded = async (required = true): Promise<boolean> => {
  const signature = stagedSignature();

  if (!signature) {
    if (!required) return true;
    step1Error.value = t('contribution.step1.errors.selectFile');
    return false;
  }
  if (signature === uploadedSignature.value) return true;

  try {
    step1Error.value = '';
    // useFileUpload owns the uploading/progress state.
    if (resourceType.value === 'text') {
      const blob = new Blob([narrativeText.value], { type: 'text/html' });
      const file = new File([blob], 'narrative_text.html', { type: 'text/html' });
      const id = await uploadOneFile(file, 'document');
      contribution.documents = [id];
      contribution.images = [];
      contribution.audio = [];
      contribution.video = [];
    } else {
      const file = stagedFile()!;
      const id = await uploadOneFile(file, resourceType.value);
      contribution.images = resourceType.value === 'image' ? [id] : [];
      contribution.audio = resourceType.value === 'audio' ? [id] : [];
      contribution.video = resourceType.value === 'video' ? [id] : [];
      contribution.documents = resourceType.value === 'document' ? [id] : [];
    }
    uploadedSignature.value = signature;
    return true;
  } catch (error) {
    const err = error as any;
    if (err?.code === 'ERR_CANCELED') return false; // user cancelled — not an error
    const status = err?.response?.status;
    const data = err?.response?.data;
    console.error('Error uploading resource:', err);
    if (status) {
      const detail = typeof data === 'string' ? data : '';
      step1Error.value = `${t('contribution.step1.errors.uploadFailedStatus', { status })} ${detail}`.trim();
    } else {
      step1Error.value = t('contribution.step1.errors.uploadFailed');
    }
    return false;
  }
};

const nextStep = async () => {
  if (submitting.value) return;

  if (currentStep.value === 1) {
    if (step1Uploading.value) return;
    const ok = await ensureResourceUploaded();
    if (!ok) return;
    currentStep.value = 2;
    return;
  }

  step1Error.value = '';
  if (currentStep.value < totalSteps) currentStep.value++;
};

const prevStep = () => {
  if (currentStep.value > 1) currentStep.value--;
};

// B2 — visible skip for the optional steps (4: details, 5: capa educativa).
const skipStep = () => {
  if (submitting.value) return;
  if (currentStep.value < totalSteps) currentStep.value++;
};

// Clear the four parallel file arrays (staged File objects) and their uploaded-id
// counterparts on `contribution`. Centralizes the reset that used to be
// copy-pasted across setResourceType / handleFileUpload / resetForm.
const clearAllMedia = () => {
  files.images = [];
  files.audio = [];
  files.video = [];
  files.documents = [];
  contribution.images = [];
  contribution.audio = [];
  contribution.video = [];
  contribution.documents = [];
  uploadedSignature.value = '';
};

const setResourceType = (nextType: ContributionResourceType) => {
  resourceType.value = nextType;
  imagePreviews.value = [];
  step1Error.value = '';
  // narrativeText kept intentionally so switching type back and forth doesn't lose it.
  abortUpload();
  clearAllMedia();
};

const onLocationUpdate = ([lat, lng]: [number, number]) => {
  formLocation.value = { lat, lng };
  contribution.location = { type: 'Point', coordinates: [lng, lat] };
  // A deliberate pin placement arms the location leg of the duplicate check.
  pinTouched.value = true;
};

// The <input id> matches the `files`/`contribution` array key; map it to the
// singular resourceType so one branch handles all four inputs.
const FILE_INPUT_TO_TYPE: Record<'images' | 'audio' | 'video' | 'documents', ContributionResourceType> = {
  images: 'image',
  audio: 'audio',
  video: 'video',
  documents: 'document',
};

const handleFileUpload = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const fileType = target.id as 'images' | 'audio' | 'video' | 'documents';
  const firstFile = target.files?.item(0);
  if (!firstFile || !(fileType in FILE_INPUT_TO_TYPE)) return;

  // B4 — catch oversize files before wasting an upload round-trip (the server
  // and nginx would reject them anyway).
  if (firstFile.size > MAX_UPLOAD_MB * 1024 * 1024) {
    step1Error.value = t('contribution.step1.errors.tooLarge', { max: MAX_UPLOAD_MB });
    target.value = '';
    return;
  }

  resourceType.value = FILE_INPUT_TO_TYPE[fileType];
  clearAllMedia();
  files[fileType] = [firstFile];

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

// One payload builder for both real submissions and drafts: the contribution
// fields, the pruned educational layer, and the B7 category suggestion.
const buildPayload = (): Record<string, any> => {
  const payload: Record<string, any> = { ...contribution };
  if (!payload.tags?.length) delete payload.tags;
  const edu = buildEducationalPayload();
  if (edu) payload.educational = edu;
  if (suggestedCategory.value.trim()) payload.suggested_category = suggestedCategory.value.trim();
  return payload;
};

const submitContribution = async () => {
  if (submitting.value || savingDraft.value) return;
  submitting.value = true;
  try {
    // In compact mode nothing was uploaded on the way in — the resource (still
    // just staged) uploads now. The wizard already uploaded it leaving step 1.
    if (compactMode.value) {
      const ok = await ensureResourceUploaded();
      if (!ok) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }
    }

    await api.post('/contributions/', buildPayload());

    queuedOffline.value = false;
    draftSaved.value = false;
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
      draftSaved.value = false;
      submittedSuccess.value = true;
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    toast.error(t('contribution.actions.error'));
  } finally {
    submitting.value = false;
  }
};

// B2 — park the work as a draft (status='draft' server-side, no moderation
// yet). Minimum viable draft = the step-2 basics; a staged resource uploads
// too when there is one, but isn't required.
const saveDraft = async () => {
  if (savingDraft.value || submitting.value) return;
  savingDraft.value = true;
  try {
    const ok = await ensureResourceUploaded(false);
    if (!ok) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    await api.post('/contributions/', { ...buildPayload(), save_as_draft: true });
    draftSaved.value = true;
    queuedOffline.value = false;
    submittedSuccess.value = true;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (error) {
    console.error('Error saving draft:', error);
    toast.error(t('contribution.actions.draftError'));
  } finally {
    savingDraft.value = false;
  }
};

// Shared 503/429/generic → localized-message mapping (also marks AI down on 503).
const { applyAIError } = useAiError();

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
    const applyEnum = (key: keyof EducationalDraft, value: string | null | undefined, allowed: readonly string[]) => {
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
  draftSaved.value = false;
  currentStep.value = 1;
  setResourceType('text'); // also clears the file/media arrays

  contribution.title = '';
  contribution.description = '';
  contribution.location = { type: 'Point', coordinates: cityDefaultLngLat() };
  contribution.address = '';
  contribution.parish = null;
  contribution.heritage_type = null;
  contribution.heritage_category = null;
  contribution.historical_period = '';
  contribution.external_registry_url = '';
  contribution.tags = [];
  tagInput.value = '';
  suggestedCategory.value = '';
  showSuggestCategory.value = false;

  possibleDuplicates.value = [];
  duplicatesDismissed.value = false;
  pinTouched.value = false;

  formLocation.value = cityDefaultLatLng();

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
const step1Valid = computed(() => {
  if (resourceType.value === 'text') {
    const plainText = narrativeText.value.replace(/<[^>]*>/g, '').trim();
    return plainText.length > 0;
  }
  if (resourceType.value === 'image') return (contribution.images?.length || files.images.length > 0) ? true : false;
  if (resourceType.value === 'audio') return (contribution.audio?.length || files.audio.length > 0) ? true : false;
  if (resourceType.value === 'video') return (contribution.video?.length || files.video.length > 0) ? true : false;
  if (resourceType.value === 'document') return (contribution.documents?.length || files.documents.length > 0) ? true : false;
  return false;
});

const isStepValid = computed(() => {
  switch (currentStep.value) {
    case 1: // Resource
      return step1Valid.value;
    case 2: // General
      return contribution.title && contribution.description && contribution.heritage_type && contribution.heritage_category;
    case 3: // Location
      return contribution.parish; // Location is defaulted, address optional
    case 4: // Details
      return true; // Optional mostly
    case 5: // Educational layer
      // Entirely optional, but a malformed learning-time value must be fixed
      // before continuing (otherwise the backend would 400 on submit).
      return !eduTimeError.value;
    case 6: // Review
      return true;
    default:
      return false;
  }
});

// B2 — a draft only needs the step-2 basics (the API's required fields).
const draftValid = computed(() =>
  !!(contribution.title && contribution.description && contribution.heritage_type && contribution.heritage_category)
);

// B2 — compact mode submits everything at once, so gate on the union of the
// per-step requirements.
const compactValid = computed(() =>
  step1Valid.value && draftValid.value && !!contribution.parish && !eduTimeError.value
);
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
      <h2 class="text-3xl font-bold text-gray-900 mb-4">
        {{ draftSaved ? t('contribution.successPage.draftTitle') : t('contribution.successPage.title') }}
      </h2>
      <p class="text-lg text-gray-600 mb-10 max-w-2xl mx-auto">
        {{ draftSaved ? t('contribution.successPage.draftMessage') : t('contribution.successPage.message') }}
      </p>
      <p v-if="queuedOffline" class="text-sm text-gray-700 mb-10 max-w-2xl mx-auto">
        {{ t('contribution.successPage.offlineQueued') }}
      </p>
      <div class="flex flex-col sm:flex-row justify-center space-y-4 sm:space-y-0 sm:space-x-4">
        <button
          v-if="draftSaved"
          @click="router.push('/my-contributions')"
          class="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-bold transition shadow-lg"
        >
          {{ t('contribution.successPage.viewMyContributions') }}
        </button>
        <button
          @click="resetForm"
          class="px-6 py-3 font-bold transition"
          :class="draftSaved
            ? 'border border-gray-300 text-gray-700 bg-white rounded-lg hover:bg-gray-50'
            : 'bg-primary-600 text-white rounded-lg hover:bg-primary-700 shadow-lg'"
        >
          {{ t('contribution.successPage.submitAnother') }}
        </button>
        <button
          @click="router.push(cityPath(''))"
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
      <div class="flex items-center justify-between gap-3">
        <span v-if="!compactMode" class="text-sm font-medium text-gray-500">{{ t('contribution.progress', { current: currentStep, total: totalSteps }) }}</span>
        <span v-else class="text-sm font-medium text-gray-500">{{ t('contribution.compact.subtitle') }}</span>
        <div class="flex items-center gap-3">
          <div v-if="!compactMode" class="flex space-x-2">
            <div v-for="step in totalSteps" :key="step"
                 class="h-2 w-10 rounded-full transition-colors duration-300"
                 :class="step <= currentStep ? 'bg-primary-600' : 'bg-gray-200'"></div>
          </div>
          <!-- B2: one-page mode for experienced contributors -->
          <button
            type="button"
            class="text-xs font-medium text-primary-700 hover:text-primary-900 underline whitespace-nowrap"
            :disabled="submitting || savingDraft || step1Uploading"
            @click="compactMode = !compactMode"
          >
            {{ compactMode ? t('contribution.compact.toWizard') : t('contribution.compact.toCompact') }}
          </button>
        </div>
      </div>
      <h2 class="text-xl font-bold text-gray-900 mt-2">
        <template v-if="compactMode">{{ t('contribution.compact.title') }}</template>
        <template v-else>
          <span v-if="currentStep === 1">{{ t('contribution.steps.1') }}</span>
          <span v-if="currentStep === 2">{{ t('contribution.steps.2') }}</span>
          <span v-if="currentStep === 3">{{ t('contribution.steps.3') }}</span>
          <span v-if="currentStep === 4">{{ t('contribution.steps.4') }}</span>
          <span v-if="currentStep === 5">{{ t('contribution.steps.5') }}</span>
          <span v-if="currentStep === 6">{{ t('contribution.steps.6') }}</span>
          <span
            v-if="currentStep === 4 || currentStep === 5"
            class="ml-2 align-middle text-xs font-medium text-gray-500 bg-gray-200 rounded-full px-2 py-0.5"
          >{{ t('contribution.optionalBadge') }}</span>
        </template>
      </h2>
    </div>

    <!-- Form Content -->
    <div class="p-8">
      <form @submit.prevent>
        
	        <!-- Step 1: Resource -->
	        <div v-if="showSection(1)" class="space-y-6">
          <h3 v-if="compactMode" class="text-lg font-bold text-gray-900">
            {{ t('contribution.steps.1') }}
          </h3>
          <div v-if="step1Uploading" class="rounded-lg border border-primary-200 bg-primary-50 p-4">
            <div class="flex items-center">
              <BaseSpinner class="h-5 w-5 text-primary-600 mr-3" />
              <div class="text-sm font-medium text-primary-900">{{ t('contribution.step1.uploading') }}</div>
            </div>
            <div class="text-xs text-primary-800 mt-1">
              <span v-if="step1UploadProgress > 0">{{ step1UploadProgress }}%</span>
              <span v-else>{{ t('contribution.step1.uploadingWait') }}</span>
            </div>
            <div v-if="step1UploadProgress > 0" class="mt-2 h-2 w-full rounded-full bg-primary-200 overflow-hidden">
              <div class="h-full bg-primary-600 transition-all" :style="{ width: `${step1UploadProgress}%` }"></div>
            </div>
            <div class="mt-3">
              <button
                type="button"
                class="text-xs font-medium text-primary-900 underline"
                @click="abortUpload()"
              >
                {{ t('contribution.step1.cancelUpload') }}
              </button>
            </div>
          </div>

	          <div class="bg-primary-50 p-4 rounded-lg text-primary-800 text-sm">
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
	                :class="resourceType === 'image' ? 'border-primary-600 bg-primary-50 text-primary-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.image') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.imageDesc') }}</div>
              </button>
	              <button
	                type="button"
	                @click="setResourceType('audio')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'audio' ? 'border-primary-600 bg-primary-50 text-primary-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.audio') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.audioDesc') }}</div>
              </button>
	              <button
	                type="button"
	                @click="setResourceType('video')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'video' ? 'border-primary-600 bg-primary-50 text-primary-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.video') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.videoDesc') }}</div>
              </button>
	              <button
	                type="button"
	                @click="setResourceType('document')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'document' ? 'border-primary-600 bg-primary-50 text-primary-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
	              >
                <div class="font-semibold">{{ t('contribution.step1.types.document') }}</div>
                <div class="text-xs text-gray-600">{{ t('contribution.step1.types.documentDesc') }}</div>
              </button>
	              <button
	                type="button"
	                @click="setResourceType('text')"
                  :disabled="step1Uploading || submitting"
	                class="px-4 py-3 rounded-lg border text-left transition"
	                :class="resourceType === 'text' ? 'border-primary-600 bg-primary-50 text-primary-900' : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'"
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
            <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step1.hints.image', { max: MAX_UPLOAD_MB }) }}</p>

            <div v-if="imagePreviews.length" class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <div class="relative group aspect-square bg-gray-100 rounded-lg overflow-hidden">
                <img :src="imagePreviews[0]" class="w-full h-full object-cover" />
              </div>
            </div>
          </div>

	          <div v-else-if="resourceType === 'audio'">
	            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.uploadLabel', { type: t('contribution.step1.types.audio') }) }}</label>
	            <input id="audio" type="file" accept="audio/*" :disabled="step1Uploading || submitting" class="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none disabled:opacity-50" @change="handleFileUpload">
	            <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step1.hints.audio', { max: MAX_UPLOAD_MB }) }}</p>
	            <p v-if="files.audio.length" class="text-xs text-gray-600 mt-1">{{ t('contribution.step1.selected', { name: files.audio[0]?.name }) }}</p>
	          </div>

	          <div v-else-if="resourceType === 'video'">
	            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.uploadLabel', { type: t('contribution.step1.types.video') }) }}</label>
	            <input id="video" type="file" accept="video/*" :disabled="step1Uploading || submitting" class="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none disabled:opacity-50" @change="handleFileUpload">
	            <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step1.hints.video', { max: MAX_UPLOAD_MB }) }}</p>
	            <p v-if="files.video.length" class="text-xs text-gray-600 mt-1">{{ t('contribution.step1.selected', { name: files.video[0]?.name }) }}</p>
	          </div>

	          <div v-else-if="resourceType === 'document'">
	            <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step1.uploadLabel', { type: t('contribution.step1.types.document') }) }}</label>
	            <input id="documents" type="file" accept="application/pdf" :disabled="step1Uploading || submitting" class="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none disabled:opacity-50" @change="handleFileUpload">
	            <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step1.hints.document', { max: MAX_UPLOAD_MB }) }}</p>
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
        <div v-if="showSection(2)" class="space-y-6" :class="{ 'mt-10 pt-8 border-t border-gray-200': compactMode }">
          <h3 v-if="compactMode" class="text-lg font-bold text-gray-900">
            {{ t('contribution.steps.2') }}
          </h3>
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
            <input v-model="contribution.title" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" :placeholder="t('contribution.step2.fields.placeholders.title')" required />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step2.fields.description') }} <span class="text-red-500">*</span></label>
            <textarea v-model="contribution.description" rows="4" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" :placeholder="t('contribution.step2.fields.placeholders.description')" required></textarea>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step2.fields.heritageType') }} <span class="text-red-500">*</span></label>
              <select v-model="contribution.heritage_type" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
                <option :value="null" disabled>{{ t('contribution.step2.fields.selectType') }}</option>
                <option v-for="t in heritageTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step2.fields.category') }} <span class="text-red-500">*</span></label>
              <select v-model="contribution.heritage_category" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
                <option :value="null" disabled>{{ t('contribution.step2.fields.selectCategory') }}</option>
                <option v-for="c in heritageCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
              <!-- B7: request-to-curator escape valve when no category fits -->
              <button
                v-if="!showSuggestCategory"
                type="button"
                class="mt-1 text-xs text-primary-700 hover:text-primary-900 underline"
                @click="showSuggestCategory = true"
              >
                {{ t('contribution.step2.suggestCategory.link') }}
              </button>
              <div v-else class="mt-2">
                <label class="block text-xs font-medium text-gray-600 mb-1">{{ t('contribution.step2.suggestCategory.label') }}</label>
                <input
                  v-model="suggestedCategory"
                  type="text"
                  maxlength="200"
                  class="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  :placeholder="t('contribution.step2.suggestCategory.placeholder')"
                />
                <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step2.suggestCategory.hint') }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- B4: near-duplicate warning (fed by title search + nearby lookup) -->
        <div
          v-if="(showSection(2) || showSection(3)) && possibleDuplicates.length && !duplicatesDismissed"
          class="mt-6 rounded-lg border border-amber-300 bg-amber-50 p-4"
        >
          <p class="text-sm font-semibold text-amber-900">{{ t('contribution.duplicates.title') }}</p>
          <p class="text-xs text-amber-800 mt-1">{{ t('contribution.duplicates.intro') }}</p>
          <ul class="mt-3 space-y-2">
            <li v-for="d in possibleDuplicates" :key="d.id" class="flex items-center justify-between gap-3 text-sm">
              <span class="text-amber-900">
                {{ d.title }}
                <span v-if="d.parish?.name" class="text-amber-700">· {{ d.parish.name }}</span>
              </span>
              <router-link
                :to="{ name: 'heritage-detail', params: { id: d.id } }"
                target="_blank"
                class="shrink-0 text-xs font-medium text-amber-900 underline hover:text-amber-950"
              >
                {{ t('contribution.duplicates.view') }}
              </router-link>
            </li>
          </ul>
          <button
            type="button"
            class="mt-3 text-xs font-medium text-amber-900 underline"
            @click="duplicatesDismissed = true"
          >
            {{ t('contribution.duplicates.dismiss') }}
          </button>
        </div>

        <!-- Step 3: Location -->
        <div v-if="showSection(3)" class="space-y-6" :class="{ 'mt-10 pt-8 border-t border-gray-200': compactMode }">
          <h3 v-if="compactMode" class="text-lg font-bold text-gray-900">
            {{ t('contribution.steps.3') }}
          </h3>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step3.fields.parish') }} <span class="text-red-500">*</span></label>
            <select v-model="contribution.parish" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
              <option :value="null" disabled>{{ t('contribution.step3.fields.selectParish') }}</option>
              <option v-for="p in parishes" :key="p.id" :value="p.id">{{ p.name }} ({{ p.canton }})</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step3.fields.address') }}</label>
            <input v-model="contribution.address" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" :placeholder="t('contribution.step3.fields.addressPlaceholder')" />
          </div>

          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="block text-sm font-medium text-gray-700">{{ t('contribution.step3.fields.pinLocation') }} <span class="text-red-500">*</span></label>
              <!-- B5: one-tap pin from the device's geolocation -->
              <button
                v-if="geoSupported"
                type="button"
                class="inline-flex items-center gap-1.5 text-sm font-medium text-primary-700 hover:text-primary-900 disabled:opacity-50"
                :disabled="locating || submitting"
                @click="useMyLocation"
              >
                <BaseSpinner v-if="locating" class="h-4 w-4" />
                <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {{ locating ? t('contribution.step3.locating') : t('contribution.step3.useMyLocation') }}
              </button>
            </div>
            <div class="h-80 rounded-lg overflow-hidden border border-gray-300">
              <LocationPickerMap
                :latlng="[formLocation.lat, formLocation.lng]"
                :zoom="zoom"
                @update:latlng="onLocationUpdate"
              />
            </div>
            <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step3.fields.coordinates', { lat: formLocation.lat.toFixed(5), lng: formLocation.lng.toFixed(5) }) }}</p>
          </div>
        </div>

        <!-- Step 4: Details -->
        <div v-if="showSection(4)" class="space-y-6" :class="{ 'mt-10 pt-8 border-t border-gray-200': compactMode }">
          <h3 v-if="compactMode" class="text-lg font-bold text-gray-900">
            {{ t('contribution.steps.4') }}
            <span class="ml-2 align-middle text-xs font-medium text-gray-500 bg-gray-200 rounded-full px-2 py-0.5">{{ t('contribution.optionalBadge') }}</span>
          </h3>
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
            <select v-model="contribution.historical_period" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
              <option value="" disabled>{{ t('contribution.step4.fields.selectPeriod') }}</option>
              <option v-for="p in historicalPeriods" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step4.fields.externalUrl') }}</label>
            <input v-model="contribution.external_registry_url" type="url" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" :placeholder="t('contribution.step4.fields.urlPlaceholder')" />
          </div>

          <!-- B1: free-form tags -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              {{ t('contribution.step4.fields.tags') }}
              <span class="text-xs font-normal text-gray-500">({{ (contribution.tags || []).length }}/{{ MAX_TAGS }})</span>
            </label>
            <div class="flex gap-2">
              <input
                v-model="tagInput"
                type="text"
                maxlength="50"
                class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                :placeholder="t('contribution.step4.fields.tagsPlaceholder')"
                :disabled="(contribution.tags || []).length >= MAX_TAGS"
                @keydown.enter.prevent="addTag()"
              />
              <button
                type="button"
                class="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                :disabled="!tagInput.trim() || (contribution.tags || []).length >= MAX_TAGS"
                @click="addTag()"
              >
                {{ t('contribution.step4.fields.addTag') }}
              </button>
            </div>
            <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step4.fields.tagsHint') }}</p>
            <div v-if="contribution.tags?.length" class="flex flex-wrap gap-2 mt-2">
              <span
                v-for="(tag, i) in contribution.tags"
                :key="tag"
                class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-primary-100 text-primary-800"
              >
                {{ tag }}
                <button type="button" class="font-bold hover:text-primary-950" :aria-label="t('contribution.step4.fields.removeTag')" @click="removeTag(i)">×</button>
              </span>
            </div>
          </div>

          <div v-if="aiSuggestedKeywords.length" class="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p class="text-sm font-medium text-gray-700 mb-2">{{ t('contribution.step4.fields.suggestedKeywords') }}</p>
            <div class="flex flex-wrap gap-2">
              <!-- Clicking a suggested keyword adopts it as a tag (B1) -->
              <button
                v-for="kw in aiSuggestedKeywords"
                :key="kw"
                type="button"
                class="inline-block px-2 py-1 text-xs rounded-full bg-primary-100 text-primary-800 hover:bg-primary-200 disabled:opacity-50"
                :disabled="(contribution.tags || []).length >= MAX_TAGS"
                :title="t('contribution.step4.fields.addAsTag')"
                @click="addTag(kw)"
              >+ {{ kw }}</button>
            </div>
            <p class="text-xs text-gray-500 mt-2">{{ t('contribution.step4.fields.suggestedKeywordsHint') }}</p>
          </div>
        </div>

        <!-- Step 5: Educational layer (IEEE-LOM) -->
        <div v-if="showSection(5)" :class="{ 'mt-10 pt-8 border-t border-gray-200': compactMode }">
          <h3 v-if="compactMode" class="text-lg font-bold text-gray-900 mb-6">
            {{ t('contribution.steps.5') }}
            <span class="ml-2 align-middle text-xs font-medium text-gray-500 bg-gray-200 rounded-full px-2 py-0.5">{{ t('contribution.optionalBadge') }}</span>
          </h3>
          <ContributionEducationStep
            :educational="educational"
            v-model:objectives-text="objectivesText"
            :ai-available="aiAvailable"
            :ai-loading="aiEduLoading"
            :ai-error="aiEduError"
            :ai-note="aiEduNote"
            :submitting="submitting"
            @sync-objectives="syncObjectivesFromText"
            @generate="generateAIEducational"
          />
        </div>

        <!-- Step 6: Review (wizard only — in compact mode the whole form IS the review) -->
        <div v-if="!compactMode && currentStep === 6" class="space-y-6">
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
              <div v-if="contribution.tags?.length" class="sm:col-span-1">
                <dt class="text-sm font-medium text-gray-500">{{ t('contribution.step4.fields.tags') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">
                  <span
                    v-for="tag in contribution.tags"
                    :key="tag"
                    class="inline-block mr-1 mb-1 px-2 py-0.5 text-xs rounded-full bg-primary-100 text-primary-800"
                  >{{ tag }}</span>
                </dd>
              </div>
              <div v-if="suggestedCategory.trim()" class="sm:col-span-1">
                <dt class="text-sm font-medium text-gray-500">{{ t('contribution.step2.suggestCategory.label') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">{{ suggestedCategory }}</dd>
              </div>
            </dl>
          </div>
        </div>

	        <!-- Navigation Buttons (wizard mode) -->
	        <div v-if="!compactMode" class="mt-8 flex items-center justify-between gap-3 pt-6 border-t border-gray-200">
          <button
            type="button"
            @click="prevStep"
            :disabled="currentStep === 1 || submitting"
            class="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
            :class="{'invisible': currentStep === 1}"
          >
            {{ t('contribution.actions.back') }}
          </button>

          <div class="flex items-center gap-3">
            <!-- B2: park the work as a draft (needs the step-2 basics) -->
            <button
              v-if="currentStep >= 2"
              type="button"
              @click="saveDraft"
              :disabled="savingDraft || submitting || !draftValid"
              class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition flex items-center"
              :title="!draftValid ? t('contribution.actions.draftNeedsBasics') : ''"
            >
              <BaseSpinner v-if="savingDraft" class="-ml-1 mr-2 h-4 w-4" />
              {{ savingDraft ? t('contribution.actions.savingDraft') : t('contribution.actions.saveDraft') }}
            </button>

            <!-- B2: visible skip on the optional steps -->
            <button
              v-if="currentStep === 4 || currentStep === 5"
              type="button"
              @click="skipStep"
              :disabled="submitting || (currentStep === 5 && !!eduTimeError)"
              class="text-sm font-medium text-gray-500 hover:text-gray-800 underline disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ t('contribution.actions.skipStep') }}
            </button>

	          <button
	            v-if="currentStep < totalSteps"
	            type="button"
	            @click="nextStep"
	            :disabled="submitting || step1Uploading || (currentStep !== 1 && !isStepValid)"
	            class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition shadow-sm"
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
        </div>

        <!-- Navigation Buttons (compact mode: everything is on screen, one send) -->
        <div v-else class="mt-10 flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3 pt-6 border-t border-gray-200">
          <button
            type="button"
            @click="saveDraft"
            :disabled="savingDraft || submitting || step1Uploading || !draftValid"
            class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition flex items-center justify-center"
            :title="!draftValid ? t('contribution.actions.draftNeedsBasics') : ''"
          >
            <BaseSpinner v-if="savingDraft" class="-ml-1 mr-2 h-4 w-4" />
            {{ savingDraft ? t('contribution.actions.savingDraft') : t('contribution.actions.saveDraft') }}
          </button>
          <button
            type="button"
            @click="submitContribution"
            :disabled="submitting || savingDraft || step1Uploading || !compactValid"
            class="px-8 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-bold transition shadow-md flex items-center justify-center"
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

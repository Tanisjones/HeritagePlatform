import axios, { AxiosHeaders } from 'axios';
import type { RouteCreateData, LessonPlanWriteData } from '@/types/heritage';
import type {
  AiUsageSummaryResponse,
  AiUsageTimeseriesResponse,
  AiUsageRecentResponse,
  AiUsageQuery,
} from '@/types/aiUsage';

const LOCALE_STORAGE_KEY = 'hp_locale';
const DEFAULT_LOCALE = 'es';

/** Login/register request bodies (the API returns `{ tokens, user }`). */
export interface LoginCredentials {
  email: string;
  password: string;
}
export interface RegisterData {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  [field: string]: unknown;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(config => {
  const headers = AxiosHeaders.from(config.headers);
  config.headers = headers;

  const token = localStorage.getItem('token');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const locale = localStorage.getItem(LOCALE_STORAGE_KEY) || DEFAULT_LOCALE;
  headers.set('Accept-Language', locale);

  // When sending FormData, do not force JSON content type (let the browser set the multipart boundary).
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    headers.delete('Content-Type');
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Clear invalid token
      localStorage.removeItem('token');
      localStorage.removeItem('user');

      // Retry the original request (now without token due to request interceptor)
      if (error.config && !error.config.__isRetry) {
        error.config.__isRetry = true;
        return api.request(error.config);
      }
    }
    return Promise.reject(error);
  }
);

export interface HeritageGeoJSON {
  type: string;
  features: {
    type: string;
    features: Array<{
      id: string;
      geometry: {
        type: string;
        coordinates: number[];
      };
      properties: {
        title: string;
        heritage_type: string;
        heritage_category: string;
        primary_image: string | null;
      };
    }>;
  };
}

export const heritageService = {
  getHeritageGeoJSON: async (): Promise<HeritageGeoJSON> => {
    const response = await api.get('/heritage-items/geojson/');
    return response.data;
  }
};

export const authService = {
  login: (credentials: LoginCredentials) => api.post('/users/login/', credentials),
  register: (data: RegisterData) => api.post('/users/register/', data),
  me: () => api.get('/users/me/'),
};

export const curatorService = {
  queue: (params?: Record<string, any>) => api.get('/moderation/queue/', { params }),
  getQueueItem: (id: string) => api.get(`/moderation/queue/${id}/`),
  approve: (id: string) => api.post(`/moderation/queue/${id}/approve/`),
  reject: (id: string, payload: { feedback?: string; curator_feedback?: string }) =>
    api.post(`/moderation/queue/${id}/reject/`, payload),
  requestChanges: (id: string, payload: { feedback?: string; curator_feedback?: string }) =>
    api.post(`/moderation/queue/${id}/request-changes/`, payload),
  getScore: (id: string) => api.get(`/moderation/queue/${id}/score/`),
  setScore: (id: string, payload: Record<string, unknown>) => api.post(`/moderation/queue/${id}/score/`, payload),
  flag: (id: string, payload: Record<string, unknown>) => api.post(`/moderation/queue/${id}/flag/`, payload),
  flags: (id: string) => api.get(`/moderation/queue/${id}/flags/`),
  resolveFlag: (flagId: string, payload: Record<string, unknown>) =>
    api.patch(`/moderation/queue/flags/${flagId}/resolve/`, payload),
  checklists: () => api.get('/moderation/queue/checklists/'),
  checklist: (id: string) => api.get(`/moderation/queue/${id}/checklist/`),
  submitChecklistResponses: (id: string, responses: Record<string, unknown>[]) =>
    api.post(`/moderation/queue/${id}/checklist-response/`, { responses }),
  notes: (id: string) => api.get(`/moderation/queue/${id}/notes/`),
  addNote: (id: string, payload: Record<string, unknown>) => api.post(`/moderation/queue/${id}/notes/`, payload),
  versions: (id: string) => api.get(`/moderation/queue/${id}/versions/`),
  stats: () => api.get('/moderation/queue/stats/'),
};

export const contributorService = {
  list: (params?: Record<string, any>) => api.get('/my-contributions/', { params }),
  get: (id: string) => api.get(`/my-contributions/${id}/`),
  update: (id: string, payload: Record<string, unknown>) => api.patch(`/my-contributions/${id}/`, payload),
  feedback: (id: string) => api.get(`/my-contributions/${id}/feedback/`),
  resubmit: (id: string) => api.post(`/my-contributions/${id}/resubmit/`),
};

export const teacherService = {
  lomPackages: (params?: Record<string, any>) => api.get('/education/lom-packages/', { params }),
  downloadLomPackage: (id: string) =>
    api.get(`/education/lom-packages/${id}/download/`, { responseType: 'blob' }),
  // The wire param is `variant`, NOT `format`: `format` is reserved by DRF
  // content negotiation and an unknown value (e.g. scorm2004) 404s server-side.
  downloadScormPackage: (heritageItemId: string, format: string = 'scorm12') =>
    api.get(`/education/scorm-packages/${heritageItemId}/download/`, {
      params: { variant: format },
      responseType: 'blob',
    }),
  // F2.c: export a whole route as one learning package (scorm12 | scorm2004 | cmi5).
  downloadRoutePackage: (routeId: string, format: string = 'scorm12') =>
    api.get(`/education/route-packages/${routeId}/download/`, {
      params: { variant: format },
      responseType: 'blob',
    }),
  // F2.c: export an arbitrary curated set of heritage items as one package.
  downloadCollectionPackage: (ids: string[], format: string = 'scorm12') =>
    api.get('/education/collection-packages/download/', {
      params: { ids: ids.join(','), variant: format },
      responseType: 'blob',
    }),
};

/**
 * Read/write access to the IEEE-LOM educational layer of a heritage item.
 *
 * The whole layer (general + nested educational / rights / lifecycle /
 * classifications) is authored in a single PATCH /lom/{id}/ against the backend
 * nested write serializer (LOMGeneralWriteSerializer). `getByHeritageItem`
 * resolves the LOMGeneral id for a heritage item so callers can then patch it.
 */
export const educationService = {
  // Resolve the LOM record for a heritage item (LOMGeneral, with nested children).
  getByHeritageItem: (heritageItemId: string) =>
    api.get('/lom/by_heritage_item/', { params: { heritage_item_id: heritageItemId } }),
  getLom: (lomId: string) => api.get(`/lom/${lomId}/`),
  // Nested partial update of the whole educational layer in one call.
  updateLom: (lomId: string, payload: Record<string, any>) =>
    api.patch(`/lom/${lomId}/`, payload),
  createLom: (payload: Record<string, any>) => api.post('/lom/', payload),
};

export const lessonPlanService = {
  list: (params?: Record<string, any>) => api.get('/lesson-plans/', { params }),
  get: (id: string) => api.get(`/lesson-plans/${id}/`),
  create: (payload: LessonPlanWriteData) => api.post('/lesson-plans/', payload),
  update: (id: string, payload: LessonPlanWriteData) => api.patch(`/lesson-plans/${id}/`, payload),
  delete: (id: string) => api.delete(`/lesson-plans/${id}/`),
  duplicate: (id: string) => api.post(`/lesson-plans/${id}/duplicate/`),
  // State machine (P.2b): draft → review → published → archived.
  submit: (id: string) => api.post(`/lesson-plans/${id}/submit/`),
  publish: (id: string) => api.post(`/lesson-plans/${id}/publish/`),
  archive: (id: string) => api.post(`/lesson-plans/${id}/archive/`),
  // Bundle the plan's linked heritage items into one SCORM collection package.
  exportScorm: (id: string, variant: 'scorm12' | 'scorm2004' = 'scorm12') =>
    api.get(`/lesson-plans/${id}/export-scorm/`, { params: { variant }, responseType: 'blob' }),
};

export const aiSuggestionService = {
  list: (params?: Record<string, any>) => api.get('/ai-suggestions/', { params }),
  approve: (id: string) => api.post(`/ai-suggestions/${id}/approve/`),
  reject: (id: string) => api.post(`/ai-suggestions/${id}/reject/`),
};

export const routeService = {
  list: (params?: Record<string, any>) => api.get('/routes/', { params }),
  get: (id: string) => api.get(`/routes/${id}/`),
  create: (payload: RouteCreateData) => api.post('/routes/', payload),
  update: (id: string, payload: Partial<RouteCreateData>) => api.patch(`/routes/${id}/`, payload),
  delete: (id: string) => api.delete(`/routes/${id}/`),

  submitForReview: (id: string) => api.post(`/routes/${id}/submit_for_review/`),
  approve: (id: string) => api.post(`/routes/${id}/approve/`),
  reject: (id: string, payload: { feedback?: string }) => api.post(`/routes/${id}/reject/`, payload),
  requestChanges: (id: string, payload: { feedback?: string }) => api.post(`/routes/${id}/request-changes/`, payload),

  archive: (id: string) => api.post(`/routes/${id}/archive/`),

  start: (id: string) => api.post(`/routes/${id}/start/`),
  checkIn: (id: string, payload: { stop_id: string; latitude?: number; longitude?: number }) =>
    api.post(`/routes/${id}/check-in/`, payload),
  skipStop: (id: string, payload: { stop_id: string }) => api.post(`/routes/${id}/skip-stop/`, payload),
  complete: (id: string) => api.post(`/routes/${id}/complete/`),

  myRoutes: (params?: Record<string, any>) => api.get('/routes/my-routes/', { params }),
  activeRoutes: (params?: Record<string, any>) => api.get('/routes/active-routes/', { params }),
  nearby: (params: { latitude: number; longitude: number; radius?: number }) =>
    api.get('/routes/nearby/', { params }),
  similar: (id: string) => api.get(`/routes/${id}/similar/`),

  // GPX/KML downloads (blob responses).
  exportGpx: (id: string) => api.get(`/routes/${id}/export-gpx/`, { responseType: 'blob' }),
  exportKml: (id: string) => api.get(`/routes/${id}/export-kml/`, { responseType: 'blob' }),

  getMyRating: (id: string) => api.get(`/routes/${id}/rate/`),
  rate: (id: string, payload: { rating: number; comment?: string }) => api.post(`/routes/${id}/rate/`, payload),
}

export const resourceService = {
  list: (params?: Record<string, any>) => api.get('/heritage-items/', { params }),
  get: (id: string) => api.get(`/heritage-items/${id}/`),
  update: (id: string, payload: Record<string, unknown>) => api.patch(`/heritage-items/${id}/`, payload),
  delete: (id: string) => api.delete(`/heritage-items/${id}/`),
};

export const routeProgressService = {
  list: (params?: Record<string, any>) => api.get('/route-progress/', { params }),
  get: (id: string) => api.get(`/route-progress/${id}/`),
};

export type PointTransaction = {
  id: string
  points: number
  reason: string
  created_at: string
}

export type UserBadge = {
  id: string
  badge: { id: number; name: string; description?: string; icon?: string | null }
  earned_at: string
}

export const gamificationService = {
  pointTransactions: (params?: Record<string, any>) => api.get('/point-transactions/', { params }),
  userBadges: (params?: Record<string, any>) => api.get('/user-badges/', { params }),
};

export type AIAssistContributionDraftRequest = {
  language?: string
  notes?: string
  title?: string
  description?: string
}

export type AIAssistContributionDraftResponse = {
  title: string
  description: string
}

export type AIAssistContributionMetadataRequest = {
  language?: string
  title?: string
  description?: string
  address?: string
  parish?: string
  heritage_type?: string
  heritage_category?: string
}

export type AIAssistContributionMetadataResponse = {
  historical_period?: string | null
  keywords: string[]
  external_registry_url?: string | null
}

export type AIAssistCuratorReviewRequest = {
  language?: string
  item?: Record<string, unknown>
  text?: string
}

export type AIAssistCuratorReviewResponse = {
  missing_fields: string[]
  risk_flags: string[]
  curator_feedback_draft: string
  suggested_edits?: Record<string, string>
}

export type AIBudgetMetric = { cap: string | number; used: string | number; remaining: string | number }
export type AIBudgetScope = { usd?: AIBudgetMetric; tokens?: AIBudgetMetric }
export type AIBudgetStatus = {
  enabled: boolean
  user: AIBudgetScope | null
  global: AIBudgetScope
}

export type AIStatusResponse = {
  available: boolean
  reason?: string
  provider?: string
  model?: string
  /** Present only when monthly budgets are configured server-side (G.6). */
  budget?: AIBudgetStatus
}

export type AIAssistEducationalMetadataRequest = {
  language?: string
  title?: string
  description?: string
  resource_type?: string
}

export type AIAssistEducationalMetadataResponse = {
  learning_resource_type?: string | null
  difficulty?: string | null
  typical_age_range?: string | null
  typical_learning_time?: string | null
  context?: string | null
  learning_objectives: string[]
  keywords: string[]
}

export type AITranslateFields = {
  title?: string
  description?: string
  keywords?: string[]
}

export type AIAssistTranslateRequest = {
  source_lang: string
  target_lang: string
  fields: AITranslateFields
}

export type AIAssistTranslateResponse = AITranslateFields

export type AIAssistRouteMetadataRequest = {
  language?: string
  title?: string
  stops?: { title?: string; description?: string }[]
}

export type AIAssistRouteMetadataResponse = {
  description?: string | null
  theme?: string | null
  difficulty?: string | null
  estimated_duration?: string | null
}

export const aiService = {
  status: async () => {
    const response = await api.get<AIStatusResponse>('/ai/status/')
    return response.data
  },
  contributionDraft: async (payload: AIAssistContributionDraftRequest) => {
    const response = await api.post<AIAssistContributionDraftResponse>('/ai/assist/contribution-draft/', payload)
    return response.data
  },
  contributionMetadata: async (payload: AIAssistContributionMetadataRequest) => {
    const response = await api.post<AIAssistContributionMetadataResponse>('/ai/assist/contribution-metadata/', payload)
    return response.data
  },
  curatorReview: async (payload: AIAssistCuratorReviewRequest) => {
    const response = await api.post<AIAssistCuratorReviewResponse>('/ai/assist/curator-review/', payload)
    return response.data
  },
  educationalMetadata: async (payload: AIAssistEducationalMetadataRequest) => {
    const response = await api.post<AIAssistEducationalMetadataResponse>('/ai/assist/educational-metadata/', payload)
    return response.data
  },
  translate: async (payload: AIAssistTranslateRequest) => {
    const response = await api.post<AIAssistTranslateResponse>('/ai/assist/translate/', payload)
    return response.data
  },
  routeMetadata: async (payload: AIAssistRouteMetadataRequest) => {
    const response = await api.post<AIAssistRouteMetadataResponse>('/ai/assist/route-metadata/', payload)
    return response.data
  },
}

/**
 * AI-economy dashboard (staff/curator). Reads the aggregation endpoints added in
 * G.4; all three share the ?since=&until= window (ISO dates, 30-day default).
 */
export const aiUsageService = {
  summary: async (params: AiUsageQuery = {}) => {
    const response = await api.get<AiUsageSummaryResponse>('/ai/usage/summary/', { params })
    return response.data
  },
  timeseries: async (params: AiUsageQuery = {}) => {
    const response = await api.get<AiUsageTimeseriesResponse>('/ai/usage/timeseries/', { params })
    return response.data
  },
  recent: async (params: AiUsageQuery = {}) => {
    const response = await api.get<AiUsageRecentResponse>('/ai/usage/recent/', { params })
    return response.data
  },
}

export default api;

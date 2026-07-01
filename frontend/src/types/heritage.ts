export interface Point {
  type: 'Point';
  coordinates: [number, number];
}

export interface Parish {
  id: number;
  name: string;
  canton?: string;
}

export interface HeritageType {
  id: number;
  name: string;
  slug: string;
}

export interface HeritageCategory {
  id: number;
  name: string;
}

export interface MediaFile {
  id: string;
  file: string;
  file_type: string;
  uploaded_at: string;
  caption?: string;
  mime_type?: string;
  text_content?: string;
}

export interface LOMRelation {
  id: string;
  lom_general?: string;
  kind: string;
  target_heritage_item?: string | null;
  target_media_file?: string | null;
  target_url?: string;
  description?: string;
}

export interface LOMGeneral {
  id?: string;
  heritage_item_id?: string;
  title?: string;
  language?: string;
  description?: string;
  keywords: string[];
  coverage: string;
  structure?: string;
  aggregation_level?: number;
  relations?: LOMRelation[];
}

export interface LOMEducational {
  id?: string;
  interactivity_type?: string;
  learning_resource_type: string;
  interactivity_level?: string;
  semantic_density?: string;
  intended_end_user_role?: string;
  context?: string;
  difficulty: string;
  typical_age_range: string;
  typical_learning_time: string;
  description?: string;
  language?: string;
  // Pedagogical (Riobamba LOM §5 extension)
  learning_objectives?: string[];
  prerequisites?: string;
  competencies?: string;
  pedagogical_approach?: string;
  curriculum_alignment?: string;
  suggested_activities?: string;
}

export interface LOMRights {
  id?: string;
  cost?: boolean;
  copyright_and_other_restrictions?: boolean;
  description?: string;
}

export interface LOMLifeCycle {
  id?: string;
  version?: string;
  status?: string;
}

export interface LOMClassification {
  id?: string;
  purpose?: string;
  taxon_source?: string;
  taxon_id?: string;
  taxon_entry?: string;
  description?: string;
  keywords?: string;
}

export interface AssessmentQuestion {
  id?: string;
  order?: number;
  question_type?: 'single_choice' | 'multiple_choice' | 'true_false' | 'short_answer';
  prompt?: string;
  choices?: Array<{ id?: string; text?: string; correct?: boolean }>;
  correct_response?: string;
  feedback?: string;
}

export interface LOMMetadata extends LOMGeneral {
  // Matches the backend LOMGeneralSerializer nested read shape.
  educational?: LOMEducational | LOMEducational[];
  rights?: LOMRights;
  lifecycle?: LOMLifeCycle;
  classifications?: LOMClassification[];
  questions?: AssessmentQuestion[];
}

export interface LOMResource {
  id: string;
  heritage_item_id?: string;
  title: string;
  description: string;
  language?: string;
  keywords?: string[];
  coverage?: string;
  educational?: LOMEducational;
}

export interface HeritageItem {
  id: string;
  status: string;
  contributor: {
    id: number;
    email: string;
  } | null;
  created_at: string;
  updated_at: string;
  title: string;
  description: string;
  location: Point;
  address: string;
  parish: Parish | null;
  heritage_type: HeritageType;
  heritage_category: HeritageCategory;
  historical_period: string;
  images: MediaFile[];
  main_image?: MediaFile;
  primary_image?: string;
  audio: MediaFile[];
  video: MediaFile[];
  documents: MediaFile[];
  lom_metadata?: LOMMetadata;
}

export interface HeritageItemContribution {
  title: string;
  description: string;
  location: Point;
  address: string;
  parish: number | null;
  heritage_type: number | null;
  heritage_category: number | null;
  historical_period: string;
  external_registry_url?: string;
  images: string[];
  audio: string[];
  video: string[];
  documents: string[];
}

export interface UserPublic {
  id: number;
  email: string;
  name: string;
  first_name: string;
  last_name: string;
}

export interface GeoJSONLineString {
  type: 'LineString';
  coordinates: [number, number][];
}

export interface RouteStop {
  id: string;
  heritage_item: HeritageItem;
  heritage_item_id?: string;
  order: number;
  arrival_instructions: string;
  suggested_time: string | null;
  audio_url?: string | null;
}

export interface RouteStep {
  instruction: string;
  distance_m: number;
  duration_s: number;
  name?: string;
}

// Awards granted for completing a route, returned by the complete() endpoint.
export interface RouteAwards {
  points: number;
  badges: string[];
}

export interface UserRouteProgress {
  id: string;
  route: string;
  started_at: string;
  completed_at: string | null;
  current_stop: RouteStop | null;
  visited_stops: RouteStop[];
  visited_stop_ids?: string[];
}

export interface RouteRating {
  id: string;
  route: string;
  user: UserPublic;
  rating: number;
  comment: string;
  created_at: string;
  updated_at: string;
}

export interface HeritageRoute {
  id: string;
  title: string;
  description: string;
  theme?: string;
  theme_category?: string | null;
  theme_category_detail?: RouteTheme | null;
  difficulty?: 'easy' | 'medium' | 'hard';
  estimated_duration?: string | null;
  distance?: number | null;
  path?: GeoJSONLineString | any | null;
  is_official?: boolean;
  status?: 'draft' | 'pending' | 'changes_requested' | 'published' | 'rejected' | 'archived';

  creator?: UserPublic | null;
  curator?: UserPublic | null;
  curator_feedback?: string;
  last_review_date?: string | null;
  submission_date?: string | null;
  priority?: number;

  wheelchair_accessible?: boolean;
  public_transit_accessible?: boolean;
  accessibility_notes?: string;

  best_season?: 'spring' | 'summer' | 'autumn' | 'winter' | 'year_round' | '';
  estimated_cost?: string | number | null;
  cost_notes?: string;

  available_languages?: string[];

  view_count?: number;
  completion_count?: number;
  average_rating?: number | null;

  created_at?: string;
  updated_at?: string;

  stop_count?: number;
  is_active?: boolean;

  stops?: RouteStop[];
  turn_by_turn?: RouteStep[];
  user_progress?: UserRouteProgress | null;
  user_rating?: RouteRating | null;
}

export interface RouteStopCreateData {
  // Present when editing an existing route, so the backend can match stops by
  // identity and preserve in-progress users' state (non-destructive update).
  id?: string;
  heritage_item_id: string;
  order: number;
  arrival_instructions?: string;
  suggested_time?: string | null;
  // Client-only helpers used by the builder map / AI button (not sent as-is; the
  // backend ignores unknown keys but the form strips them before submit).
  location?: Point | null;
  title?: string;
}

export interface RouteTheme {
  id: string;
  name: string;
  slug: string;
  description?: string;
  color?: string;
}

export interface RouteCreateData {
  title: string;
  description: string;
  theme?: string;
  /** FK to a curated RouteTheme (H.2); the `theme` string is denormalized server-side. */
  theme_category?: string | null;
  difficulty?: 'easy' | 'medium' | 'hard';
  estimated_duration?: string | null;
  distance?: number | null;
  path?: GeoJSONLineString | any | null;
  wheelchair_accessible?: boolean;
  public_transit_accessible?: boolean;
  accessibility_notes?: string;
  best_season?: 'spring' | 'summer' | 'autumn' | 'winter' | 'year_round' | '';
  estimated_cost?: string | number | null;
  cost_notes?: string;
  available_languages?: string[];
  stops?: RouteStopCreateData[];
}

export interface ResourceType {
  id: number;
  name: string;
}

export interface ResourceCategory {
  id: number;
  name: string;
}

export interface EducationalResource {
  id: number;
  title: string;
  description: string;
  resource_type: ResourceType | null;
  category: ResourceCategory | null;
  author: {
    id: number;
    email: string;
  } | null;
  content: string;
}

// --- Pedagogical authoring: Lesson Plans (see IMPROVEMENT_PLAN_V2 · Pilar P) ---

export type LessonActivityType = 'hook' | 'explore' | 'explain' | 'practice' | 'assess' | 'reflect';

export interface LessonActivity {
  id?: string;
  order: number;
  title: string;
  activity_type: LessonActivityType;
  instructions?: string;
  duration_minutes?: number | null;
  materials?: string;
  heritage_item?: string | null;
  route?: string | null;
  educational_resource?: number | null;
  lom_general?: string | null;
  // Read-only labels for bound content (server-provided).
  heritage_item_title?: string | null;
  route_title?: string | null;
  educational_resource_title?: string | null;
}

export type LessonPlanStatus = 'draft' | 'review' | 'published' | 'archived';
export type LessonPlanVisibility = 'private' | 'unlisted' | 'public';

export interface CurriculumStandard {
  id: string;
  code: string;
  subject?: string;
  grade_level?: string;
  description: string;
}

export interface RubricCriterion {
  id?: string;
  order: number;
  label: string;
  max_points: number;
  levels: Array<{ level?: string; points?: number; descriptor?: string }>;
}

export interface Rubric {
  id?: string;
  lesson?: string;
  title: string;
  description?: string;
  criteria: RubricCriterion[];
}

export interface LessonPlan {
  id: string;
  title: string;
  summary?: string;
  objectives: string[];
  standards?: string[];
  standards_detail?: CurriculumStandard[];
  rubrics?: Rubric[];
  subject?: string;
  grade_level?: string;
  audience?: string;
  curriculum_alignment?: string;
  pedagogical_approach?: string;
  estimated_total_minutes?: number | null;
  status: LessonPlanStatus;
  visibility: LessonPlanVisibility;
  related_route?: string | null;
  author?: number | null;
  author_name?: string | null;
  activities: LessonActivity[];
  created_at?: string;
  updated_at?: string;
}

/** Write shape for creating/updating a lesson plan (nested activities reconciled by id). */
export type LessonPlanWriteData = Partial<Omit<LessonPlan, 'id' | 'author' | 'author_name' | 'created_at' | 'updated_at'>>;

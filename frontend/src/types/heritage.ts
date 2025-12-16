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
  title?: string;
  language?: string;
  description?: string;
  keywords: string[];
  coverage: string;
  relations?: LOMRelation[];
}

export interface LOMEducational {
  id: string;
  interactivity_type?: string;
  learning_resource_type: string;
  interactivity_level?: string;
  semantic_density?: string;
  intended_end_user_role?: string;
  context?: string;
  difficulty: string;
  typical_age_range: string;
  typical_learning_time: string;
  language?: string;
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
}

export interface LOMMetadata extends LOMGeneral {
  educational?: LOMEducational | LOMEducational[];
  rights?: LOMRights;
  life_cycle?: LOMLifeCycle;
  classification?: LOMClassification;
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
  user_progress?: UserRouteProgress | null;
  user_rating?: RouteRating | null;
}

export interface RouteStopCreateData {
  heritage_item_id: string;
  order: number;
  arrival_instructions?: string;
  suggested_time?: string | null;
}

export interface RouteCreateData {
  title: string;
  description: string;
  theme?: string;
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

import type { CityRef } from './city';

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type ContributionStatus =
  | 'draft'
  | 'pending'
  | 'changes_requested'
  | 'published'
  | 'rejected'
  | 'archived';

export interface QualityScore {
  id?: string;
  heritage_item?: string;
  completeness_score: number;
  accuracy_score: number;
  media_quality_score: number;
  total_score?: number;
  scored_by?: number | null;
  scored_at?: string;
  notes?: string;
}

export type FlagType =
  | 'spam'
  | 'inappropriate'
  | 'duplicate'
  | 'expert_review_needed'
  | 'copyright_issue'
  | 'inaccurate';

export type FlagStatus = 'open' | 'under_review' | 'resolved' | 'dismissed';

export interface ContributionFlag {
  id: string;
  heritage_item: string;
  flag_type: FlagType;
  status: FlagStatus;
  reason?: string;
  flagged_by?: number | null;
  resolved_by?: number | null;
  resolution_notes?: string;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContributionVersion {
  id: string;
  heritage_item: string;
  version_number: number;
  created_by?: number | null;
  created_by_type: 'contributor' | 'curator' | 'system';
  data_snapshot: unknown;
  changes_summary?: string;
  created_at: string;
}

export interface ReviewChecklistItem {
  id: string;
  text: string;
  help_text?: string;
  order: number;
  is_required: boolean;
}

export interface ReviewChecklist {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  applicable_to_types: number[];
  applicable_to_categories: number[];
  items: ReviewChecklistItem[];
}

export interface ReviewChecklistResponse {
  id?: string;
  heritage_item: string;
  checklist_item: string;
  curator?: number | null;
  is_checked: boolean;
  notes?: string;
  created_at?: string;
}

export interface CuratorNote {
  id: string;
  heritage_item: string;
  curator?: number | null;
  content: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface CuratorQueueItem {
  id: string;
  title: string;
  description: string;
  status: ContributionStatus;
  created_at: string;
  flags_open?: number;
  total_score?: number | null;
  priority?: number;
  submission_date?: string | null;
  last_review_date?: string | null;
  /** C1 — present on queue rows (CityRef); shown as a badge when unscoped. */
  city?: { id: number; slug: string; name: string } | null;
  /** D2 — who claimed the item; null when unassigned. */
  curator_email?: string | null;
  parish?: unknown;
  heritage_type?: unknown;
  heritage_category?: unknown;
  contributor?: unknown;
  curator?: unknown;
  images?: unknown[];
}

/** A media file attached to a heritage item, as returned in the review detail. */
export interface CuratorReviewMedia {
  id: string;
  file: string;
  [key: string]: unknown;
}

/**
 * The heritage item under review, as embedded in CuratorReviewDetail. Modeled
 * explicitly so the review view can drop its ~27 `(detail as any)` casts.
 */
export interface CuratorHeritageItem {
  id: string;
  title?: string;
  description?: string;
  status?: string;
  /** Owning city (HeritageItemDetailSerializer.city) — the item's own city,
   *  which is not necessarily the curator's active one. */
  city?: CityRef | null;
  address?: string;
  historical_period?: string | null;
  heritage_type?: { name?: string } | null;
  heritage_category?: { name?: string } | null;
  parish?: { name?: string } | null;
  location?: string | { type?: string; coordinates?: number[] } | null;
  images?: CuratorReviewMedia[];
  audio?: CuratorReviewMedia[];
  video?: CuratorReviewMedia[];
  documents?: CuratorReviewMedia[];
  [key: string]: unknown;
}

export interface CuratorReviewDetail {
  heritage_item: CuratorHeritageItem;
  quality_score?: QualityScore;
  flags: ContributionFlag[];
  checklist_responses: ReviewChecklistResponse[];
  curator_notes: CuratorNote[];
  versions: ContributionVersion[];
}

export interface CuratorStats {
  pending: number;
  changes_requested: number;
  flagged_open: number;
  reviewed_total: number;
  /** D1 — per-city workload across the cities this curator governs. */
  cities?: Array<{ slug: string; name: string; pending: number; changes_requested: number }>;
}

export interface ContributorFeedback {
  status: ContributionStatus;
  curator_feedback: string;
  quality_score: (QualityScore & { scored_at?: string }) | null;
}


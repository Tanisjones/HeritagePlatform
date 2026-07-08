import type { Point } from './heritage';

/** A city hosting its own heritage content on the shared platform. */
export interface City {
  id: number;
  slug: string;
  name: string;
  description?: string;
  country: string;
  country_name?: string;
  region?: string;
  timezone: string;
  /** GeoJSON Point — coordinates are [lng, lat]. */
  center: Point;
  default_zoom: number;
  boundary?: unknown | null;
  default_language: string;
  hero_image?: string | null;
  is_active: boolean;
}

/** Compact reference embedded on city-scoped content. */
export interface CityRef {
  id: number;
  slug: string;
  name: string;
}

/** Per-city governance grant exposed on /users/me. */
export interface CityRoleAssignment {
  city: CityRef;
  role: 'curator' | 'moderator';
}

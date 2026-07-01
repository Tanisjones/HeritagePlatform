import 'vue-router'

/**
 * Type augmentation for route `meta`. Lets the navigation guard read
 * `record.meta.requiresAuth` etc. with full typing instead of the
 * `(record.meta as any)` casts that used to be in router/index.ts.
 */
declare module 'vue-router' {
  interface RouteMeta {
    /** Route requires an authenticated user. */
    requiresAuth?: boolean
    /** Route is only for guests (redirects authed users to /dashboard). */
    guestOnly?: boolean
    /** Route requires curator (or staff) privileges. */
    requiresCurator?: boolean
    /** Route requires teacher (or staff) privileges. */
    requiresTeacher?: boolean
  }
}

import type { RouterScrollBehavior } from 'vue-router'

/**
 * Scroll policy for the SPA.
 *
 * The subtlety: several views (ExploreView above all) push their filter state
 * into the query with `router.replace`, which vue-router reports as a real
 * navigation. Scrolling to top there would yank the reader back to the header
 * on every filter change, tag chip and search keystroke — so an in-place
 * change of the same path is explicitly *not* a scroll event.
 */
export const scrollBehavior: RouterScrollBehavior = (to, from, savedPosition) => {
  // Back/forward: restore where the user was.
  if (savedPosition) return savedPosition
  // Same path, different query/hash: an in-place URL sync, not a navigation.
  if (to.path === from.path) return false
  if (to.hash) return { el: to.hash }
  return { top: 0 }
}

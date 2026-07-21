import { describe, expect, it } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'
import { scrollBehavior } from '@/router/scroll'

/** Minimal route stand-in — scrollBehavior only reads `path` and `hash`. */
function loc(path: string, hash = ''): RouteLocationNormalized {
  return { path, hash } as RouteLocationNormalized
}

// The behaviour is only meaningful synchronously; vue-router types it as
// possibly-async, so narrow it for the assertions.
const scroll = (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  saved: { left: number; top: number } | null = null,
) => scrollBehavior(to, from, saved)

describe('scrollBehavior', () => {
  it('restores the saved position on back/forward', () => {
    expect(scroll(loc('/riobamba/explore'), loc('/riobamba'), { left: 0, top: 640 })).toEqual({
      left: 0,
      top: 640,
    })
  })

  it('does NOT scroll when only the query changes (ExploreView filter syncs)', () => {
    // router.replace({ query }) keeps the path — scrolling here would throw the
    // reader back to the header on every filter change and search keystroke.
    expect(scroll(loc('/riobamba/explore'), loc('/riobamba/explore'))).toBe(false)
  })

  it('scrolls to top on a real navigation', () => {
    expect(scroll(loc('/riobamba/routes'), loc('/riobamba/explore'))).toEqual({ top: 0 })
  })

  it('scrolls to the anchor when the target has a hash', () => {
    expect(scroll(loc('/riobamba/heritage/42', '#media'), loc('/riobamba/explore'))).toEqual({
      el: '#media',
    })
  })

  it('treats a cross-city navigation as a real navigation', () => {
    expect(scroll(loc('/tarragona/explore'), loc('/riobamba/explore'))).toEqual({ top: 0 })
  })
})

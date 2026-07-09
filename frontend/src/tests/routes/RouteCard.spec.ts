import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createPinia } from 'pinia'

// The city store (used for the C1 badge) reads localStorage at setup; this
// spec's environment has none — give it a minimal in-memory one.
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (key: string) => backing.get(key) ?? null,
  setItem: (key: string, value: string) => void backing.set(key, String(value)),
  removeItem: (key: string) => void backing.delete(key),
  clear: () => backing.clear(),
})

import RouteCard from '@/components/routes/RouteCard.vue'

describe('RouteCard', () => {
  it('renders title, description and theme chip', () => {
    const wrapper = mount(RouteCard, {
      props: {
        route: {
          id: 'r1',
          title: 'My Route',
          description: 'A nice walk',
          status: 'draft',
          stop_count: 2,
          difficulty: 'easy',
          theme: 'Ruta colonial',
        } as any,
      },
      global: {
        // RouteCard reads the city store (C1 badge) — needs a Pinia instance.
        plugins: [createPinia()],
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    expect(wrapper.text()).toContain('My Route')
    expect(wrapper.text()).toContain('A nice walk')
    // The status is rendered through i18n (Spanish by default): "draft" -> "Borrador".
    expect(wrapper.text()).toContain('Borrador')
    // C6: the theme chip renders (free-text fallback when no catalog entry).
    expect(wrapper.text()).toContain('Ruta colonial')
  })
})


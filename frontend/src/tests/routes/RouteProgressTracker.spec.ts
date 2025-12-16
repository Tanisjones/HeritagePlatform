import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RouteProgressTracker from '@/components/routes/RouteProgressTracker.vue'

describe('RouteProgressTracker', () => {
  it('shows correct visited counts and percent', () => {
    const wrapper = mount(RouteProgressTracker, {
      props: {
        stops: [
          { id: 's1', order: 1, heritage_item: { id: 'h1', title: 'A', location: { type: 'Point', coordinates: [0, 0] } } },
          { id: 's2', order: 2, heritage_item: { id: 'h2', title: 'B', location: { type: 'Point', coordinates: [0, 0] } } },
        ] as any,
        progress: {
          id: 'p1',
          route: 'r1',
          started_at: '2025-01-01T00:00:00Z',
          completed_at: null,
          current_stop: null,
          visited_stops: [{ id: 's1', order: 1, heritage_item: { id: 'h1', title: 'A', location: { type: 'Point', coordinates: [0, 0] } } }] as any,
        } as any,
      },
    })

    expect(wrapper.text()).toContain('1 / 2')
    expect(wrapper.text()).toContain('50%')
    expect(wrapper.text()).toContain('Next:')
  })
})


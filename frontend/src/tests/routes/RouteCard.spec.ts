import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RouteCard from '@/components/routes/RouteCard.vue'

describe('RouteCard', () => {
  it('renders title and description', () => {
    const wrapper = mount(RouteCard, {
      props: {
        route: {
          id: 'r1',
          title: 'My Route',
          description: 'A nice walk',
          status: 'draft',
          stop_count: 2,
          difficulty: 'easy',
        } as any,
      },
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    expect(wrapper.text()).toContain('My Route')
    expect(wrapper.text()).toContain('A nice walk')
    expect(wrapper.text()).toContain('draft')
  })
})


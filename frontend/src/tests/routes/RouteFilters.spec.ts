import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RouteFilters from '@/components/routes/RouteFilters.vue'

describe('RouteFilters', () => {
  it('emits change when inputs update', async () => {
    const wrapper = mount(RouteFilters)

    const search = wrapper.find('input')
    await search.setValue('downtown')

    const emitted = wrapper.emitted('change')
    expect(emitted).toBeTruthy()
    const lastEvent = emitted ? (emitted[emitted.length - 1] as any) : null
    const last = lastEvent?.[0] as any
    expect(last.search).toBe('downtown')
  })
})

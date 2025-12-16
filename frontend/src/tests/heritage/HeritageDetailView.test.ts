import { describe, it, expect, vi, beforeEach } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'

// Avoid bringing in Leaflet CSS into the test environment.
vi.mock('leaflet/dist/leaflet.css', () => ({}))

// Mock i18n to keep rendering simple/stable.
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
    te: () => false,
  }),
}))

// Mock route param used by the detail view.
vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: 'test-id' },
    query: {},
  }),
}))

// Mock map components.
vi.mock('@vue-leaflet/vue-leaflet', () => ({
  LMap: { name: 'LMap', template: '<div />' },
  LTileLayer: { name: 'LTileLayer', template: '<div />' },
  LMarker: { name: 'LMarker', template: '<div />' },
}))

const apiGetMock = vi.fn()
vi.mock('@/services/api', () => ({
  default: {
    get: (...args: any[]) => apiGetMock(...args),
  },
}))

import HeritageDetailView from '@/views/heritage/HeritageDetailView.vue'

describe('HeritageDetailView media viewers', () => {
  beforeEach(() => {
    apiGetMock.mockReset()
  })

  it('renders correct viewer for video/audio/image/pdf/text', async () => {
    apiGetMock.mockResolvedValue({
      data: {
        id: 'item-1',
        title: 'Item',
        description: 'Desc',
        location: { coordinates: [-78.65, -1.67] },
        heritage_type: { name: 'Tangible' },
        heritage_category: { name: 'Architecture' },
        parish: { name: 'Parish' },
        address: '',
        primary_image: null,
        lom_metadata: {
          // Use a non-text resource type so the view doesn't reorder media to documents-first.
          educational: { learning_resource_type: 'simulation' },
        },
        video: [{ id: 'v1', file: 'https://example.test/video.mp4', mime_type: 'video/mp4' }],
        audio: [{ id: 'a1', file: 'https://example.test/audio.mp3', mime_type: 'audio/mpeg' }],
        images: [
          {
            id: 'i1',
            file: 'https://example.test/image.png',
            mime_type: 'image/png',
            caption: 'Image caption',
          },
        ],
        documents: [
          { id: 'd1', file: 'https://example.test/doc.pdf', mime_type: 'application/pdf' },
          { id: 't1', file: 'https://example.test/text.txt', mime_type: 'text/plain' },
        ],
      },
    })

    const wrapper = shallowMount(HeritageDetailView, {
      global: {
        stubs: {
          AnnotationList: true,
          'router-link': true,
        },
      },
    })

    await flushPromises()

    // Default active media is the first entry: video.
    expect(wrapper.find('video').exists()).toBe(true)

    const playlistButtons = wrapper.findAll('button')
    // There are many buttons in the page; filter down to the media playlist.
    // Playlist buttons are the ones with fixed thumbnail size class.
    const mediaButtons = playlistButtons.filter((b) => b.classes().includes('w-24') && b.classes().includes('h-16'))

    expect(mediaButtons.length).toBe(5)

    // Click Audio (index 1)
    await mediaButtons[1]!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('audio').exists()).toBe(true)

    // Click Image (index 2)
    await mediaButtons[2]!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('img').exists()).toBe(true)

    // Click PDF (index 3) -> iframe
    await mediaButtons[3]!.trigger('click')
    await wrapper.vm.$nextTick()
    const pdfFrame = wrapper.find('iframe')
    expect(pdfFrame.exists()).toBe(true)
    expect(pdfFrame.attributes('src')).toBe('https://example.test/doc.pdf')

    // Click Text (index 4) -> iframe
    await mediaButtons[4]!.trigger('click')
    await wrapper.vm.$nextTick()
    const textFrame = wrapper.find('iframe')
    expect(textFrame.exists()).toBe(true)
    expect(textFrame.attributes('src')).toBe('https://example.test/text.txt')
  })
})

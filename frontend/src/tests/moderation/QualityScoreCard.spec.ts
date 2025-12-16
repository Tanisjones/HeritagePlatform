import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import QualityScoreCard from '@/components/moderation/QualityScoreCard.vue'

describe('QualityScoreCard', () => {
    it('renders initial scores correctly', () => {
        const scores = {
            completeness_score: 10,
            accuracy_score: 10,
            media_quality_score: 10,
            notes: ''
        }
        const wrapper = mount(QualityScoreCard, {
            props: { modelValue: scores }
        })

        expect(wrapper.text()).toContain('Total: 30/100')
    })

    it('updates total when input changes', async () => {
        const scores = { completeness_score: 0, accuracy_score: 0, media_quality_score: 0, notes: '' }
        const wrapper = mount(QualityScoreCard, {
            props: { modelValue: scores }
        })

        const input = wrapper.find('input[type="range"]')
        await input.setValue(20)

        // Since total is computed, check if emitted value has new total
        const emitted = wrapper.emitted('update:modelValue')
        expect(emitted).toBeTruthy()
        expect(emitted?.[0]?.[0]).toMatchObject({
            completeness_score: 20,
            total_score: 20
        })
    })

    it('emits save event', async () => {
        const scores = { completeness_score: 0, accuracy_score: 0, media_quality_score: 0 }
        const wrapper = mount(QualityScoreCard, {
            props: { modelValue: scores }
        })

        await wrapper.find('button').trigger('click')
        expect(wrapper.emitted('save')).toBeTruthy()
    })
})

<script setup lang="ts">
/**
 * Tiny dependency-free line chart (inline SVG) for the AI-usage timeseries.
 *
 * Deliberately minimal — one metric, one polyline, area fill, hover dots with a
 * native <title> tooltip. Avoids pulling chart.js just to draw a single series
 * (per the G.5 "don't over-engineer" note). Uses the terracotta `primary` brand.
 */
import { computed } from 'vue'

interface Point {
  date: string
  value: number
}

const props = withDefaults(
  defineProps<{
    points: Point[]
    /** For the y-axis / tooltip formatting. */
    valueLabel?: string
    /** Optional formatter for the tooltip value. */
    format?: (v: number) => string
    height?: number
  }>(),
  { valueLabel: '', height: 220 },
)

const WIDTH = 640
const PAD = { top: 16, right: 16, bottom: 28, left: 48 }

const geometry = computed(() => {
  const pts = props.points
  const h = props.height
  const innerW = WIDTH - PAD.left - PAD.right
  const innerH = h - PAD.top - PAD.bottom

  if (pts.length === 0) {
    return { coords: [] as { x: number; y: number; p: Point }[], max: 0, path: '', area: '' }
  }

  const max = Math.max(1, ...pts.map((p) => p.value))
  const stepX = pts.length > 1 ? innerW / (pts.length - 1) : 0
  const coords = pts.map((p, i) => {
    const x = PAD.left + (pts.length > 1 ? i * stepX : innerW / 2)
    const y = PAD.top + innerH - (p.value / max) * innerH
    return { x, y, p }
  })

  const path = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(' ')
  const baseline = PAD.top + innerH
  const first = coords[0]
  const last = coords[coords.length - 1]
  const area =
    first && last
      ? `${path} L ${last.x.toFixed(1)} ${baseline} L ${first.x.toFixed(1)} ${baseline} Z`
      : ''

  return { coords, max, path, area, baseline, innerH }
})

const yTicks = computed(() => {
  const max = geometry.value.max
  const steps = 4
  return Array.from({ length: steps + 1 }, (_, i) => {
    const value = (max / steps) * i
    const innerH = props.height - PAD.top - PAD.bottom
    const y = PAD.top + innerH - (value / max) * innerH
    return { y, value }
  })
})

function fmt(v: number): string {
  return props.format ? props.format(v) : String(Math.round(v))
}
</script>

<template>
  <div class="w-full overflow-x-auto">
    <svg
      :viewBox="`0 0 ${WIDTH} ${height}`"
      class="w-full"
      :style="{ minWidth: '320px' }"
      role="img"
      :aria-label="valueLabel"
    >
      <!-- gridlines + y-axis labels -->
      <g>
        <line
          v-for="(t, i) in yTicks"
          :key="`grid-${i}`"
          :x1="PAD.left"
          :x2="WIDTH - PAD.right"
          :y1="t.y"
          :y2="t.y"
          stroke="var(--color-neutral-200, #e7e5e4)"
          stroke-width="1"
        />
        <text
          v-for="(t, i) in yTicks"
          :key="`ylab-${i}`"
          :x="PAD.left - 8"
          :y="t.y + 3"
          text-anchor="end"
          font-size="10"
          fill="var(--color-neutral-500, #78716c)"
        >
          {{ fmt(t.value) }}
        </text>
      </g>

      <template v-if="geometry.coords.length">
        <!-- area fill -->
        <path :d="geometry.area" fill="var(--color-primary-100, #fae7e0)" opacity="0.7" />
        <!-- line -->
        <path :d="geometry.path" fill="none" stroke="var(--color-primary-600, #b55a3a)" stroke-width="2" />
        <!-- dots -->
        <g>
          <circle
            v-for="(c, i) in geometry.coords"
            :key="`dot-${i}`"
            :cx="c.x"
            :cy="c.y"
            r="3"
            fill="var(--color-primary-600, #b55a3a)"
          >
            <title>{{ c.p.date }} — {{ fmt(c.p.value) }} {{ valueLabel }}</title>
          </circle>
        </g>
      </template>
    </svg>
  </div>
</template>

import type { City } from '@/types/city'

/**
 * C3 — per-city theming. The Tailwind v4 palette lives in CSS custom
 * properties (`--color-primary-*` in style.css), so re-theming the whole app
 * around a city's brand color is a matter of overriding those variables on
 * :root with a ramp derived from one hex value. Cities without a brand color
 * get the platform default (overrides removed).
 */

// Same steps the hand-tuned platform palette follows: tints toward white,
// shades toward black, brand at 500.
const RAMP: Array<[step: number, mix: number, toward: 'white' | 'black']> = [
  [50, 0.94, 'white'],
  [100, 0.86, 'white'],
  [200, 0.72, 'white'],
  [300, 0.55, 'white'],
  [400, 0.3, 'white'],
  [500, 0, 'white'],
  [600, 0.12, 'black'],
  [700, 0.26, 'black'],
  [800, 0.38, 'black'],
  [900, 0.5, 'black'],
]

function parseHex(hex: string): [number, number, number] | null {
  const m = /^#([0-9a-f]{6})$/i.exec(hex.trim())
  const value = m?.[1]
  if (!value) return null
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16),
  ]
}

function mix(rgb: [number, number, number], amount: number, toward: 'white' | 'black'): string {
  const target = toward === 'white' ? 255 : 0
  const channel = (c: number) => Math.round(c + (target - c) * amount)
  return `rgb(${channel(rgb[0])}, ${channel(rgb[1])}, ${channel(rgb[2])})`
}

function themeColorMeta(): HTMLMetaElement {
  let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'theme-color'
    document.head.appendChild(meta)
  }
  return meta
}

/** Apply (or clear, when the city has no brand color) the per-city palette. */
export function applyCityTheme(city: City | null | undefined): void {
  const root = document.documentElement
  const rgb = city?.brand_color ? parseHex(city.brand_color) : null

  for (const [step, amount, toward] of RAMP) {
    const prop = `--color-primary-${step}`
    if (rgb) {
      root.style.setProperty(prop, mix(rgb, amount, toward))
    } else {
      root.style.removeProperty(prop)
    }
  }

  // Browser chrome accent (PWA/mobile address bar). Platform default matches
  // the stock primary-600.
  themeColorMeta().content = rgb && city?.brand_color ? city.brand_color : '#b55a3a'
}

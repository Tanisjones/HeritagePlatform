import { describe, expect, it } from 'vitest'
import { haversineMeters, boundingBox, lngLatToTile, type LngLat } from '@/utils/geo'

describe('geo utils', () => {
  it('haversineMeters ~ correct for two Riobamba points', () => {
    const a: LngLat = [-78.6479, -1.6735]
    const b: LngLat = [-78.644, -1.67]
    const d = haversineMeters(a, b)
    expect(d).toBeGreaterThan(400)
    expect(d).toBeLessThan(800)
  })

  it('haversineMeters is 0 for identical points', () => {
    expect(haversineMeters([-78.6, -1.6], [-78.6, -1.6])).toBe(0)
  })

  it('boundingBox spans all points', () => {
    const bbox = boundingBox([
      [-78.65, -1.68],
      [-78.64, -1.67],
      [-78.66, -1.66],
    ])
    expect(bbox).toEqual([-78.66, -1.68, -78.64, -1.66])
  })

  it('boundingBox is null for empty input', () => {
    expect(boundingBox([])).toBeNull()
  })

  it('lngLatToTile returns in-range tile indices', () => {
    const { x, y } = lngLatToTile(-78.6479, -1.6735, 14)
    const n = 2 ** 14
    expect(x).toBeGreaterThanOrEqual(0)
    expect(x).toBeLessThan(n)
    expect(y).toBeGreaterThanOrEqual(0)
    expect(y).toBeLessThan(n)
  })
})

import { describe, expect, it } from 'vitest'
import {
  haversineMeters,
  boundingBox,
  lngLatToTile,
  parsePoint,
  parseLineString,
  type LngLat,
} from '@/utils/geo'

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

describe('WKT / GeoJSON parsing', () => {
  it('parsePoint reads SRID-prefixed WKT into [lat, lng]', () => {
    expect(parsePoint('SRID=4326;POINT (-78.6479 -1.6735)')).toEqual([-1.6735, -78.6479])
  })

  it('parsePoint reads bare WKT POINT', () => {
    expect(parsePoint('POINT(-78.65 -1.67)')).toEqual([-1.67, -78.65])
  })

  it('parsePoint tolerates signs and scientific notation', () => {
    expect(parsePoint('POINT (1.5e-3 -1.6)')).toEqual([-1.6, 0.0015])
    expect(parsePoint('POINT (+78.6 -1.6)')).toEqual([-1.6, 78.6])
  })

  it('parsePoint reads a GeoJSON Point object into [lat, lng]', () => {
    expect(parsePoint({ type: 'Point', coordinates: [-78.65, -1.67] })).toEqual([-1.67, -78.65])
  })

  it('parsePoint returns null for empty/garbage', () => {
    expect(parsePoint(null)).toBeNull()
    expect(parsePoint('')).toBeNull()
    expect(parsePoint('POINT()')).toBeNull()
    expect(parsePoint({ type: 'Point' })).toBeNull()
  })

  it('parsePoint does not mis-parse a non-POINT WKT geometry', () => {
    // A POLYGON's first vertex must NOT be returned as if it were a Point.
    expect(parsePoint('POLYGON ((-78.65 -1.67, -78.64 -1.66, -78.63 -1.67, -78.65 -1.67))')).toBeNull()
    expect(parsePoint('LINESTRING (-78.65 -1.67, -78.64 -1.66)')).toBeNull()
  })

  it('parseLineString reads WKT LINESTRING into [lat, lng] pairs', () => {
    expect(parseLineString('LINESTRING (-78.65 -1.67, -78.64 -1.66)')).toEqual([
      [-1.67, -78.65],
      [-1.66, -78.64],
    ])
  })

  it('parseLineString reads a GeoJSON LineString object', () => {
    expect(
      parseLineString({
        type: 'LineString',
        coordinates: [
          [-78.65, -1.67],
          [-78.64, -1.66],
        ],
      }),
    ).toEqual([
      [-1.67, -78.65],
      [-1.66, -78.64],
    ])
  })

  it('parseLineString returns null for non-linestring input', () => {
    expect(parseLineString(null)).toBeNull()
    expect(parseLineString('POINT (-78.65 -1.67)')).toBeNull()
    expect(parseLineString({ type: 'Point', coordinates: [-78.65, -1.67] })).toBeNull()
  })
})

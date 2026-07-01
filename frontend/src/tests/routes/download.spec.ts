import { describe, expect, it } from 'vitest'
import { slugifyFilename, readBlobError } from '@/utils/download'

describe('download utils', () => {
  it('slugifyFilename sanitizes and collapses', () => {
    expect(slugifyFilename('Ruta Centro Histórico!')).toBe('Ruta-Centro-Hist-rico')
    expect(slugifyFilename('  a  b  ')).toBe('a-b')
    expect(slugifyFilename('', 'route')).toBe('route')
    expect(slugifyFilename('---')).toBe('download')
  })

  it('readBlobError reads a Blob error body as text', async () => {
    const err = { response: { data: new Blob(['boom'], { type: 'text/plain' }) } }
    await expect(readBlobError(err, 'fallback')).resolves.toBe('boom')
  })

  it('readBlobError falls back when not a blob', async () => {
    await expect(readBlobError({ message: 'x' }, 'fallback')).resolves.toBe('fallback')
  })
})

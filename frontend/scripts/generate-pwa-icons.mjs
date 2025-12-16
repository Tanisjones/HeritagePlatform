import fs from 'node:fs/promises'
import path from 'node:path'
import sharp from 'sharp'

const projectRoot = path.resolve(new URL('.', import.meta.url).pathname, '..')
const publicDir = path.join(projectRoot, 'public')
const srcIcon = path.join(publicDir, 'vite.svg')
const iconsDir = path.join(publicDir, 'icons')

await fs.mkdir(iconsDir, { recursive: true })

const targets = [
  { size: 192, file: 'icon-192.png' },
  { size: 512, file: 'icon-512.png' },
]

for (const { size, file } of targets) {
  const outPath = path.join(iconsDir, file)
  await sharp(srcIcon)
    .resize(size, size, { fit: 'contain', background: { r: 250, g: 250, b: 249, alpha: 1 } })
    .png()
    .toFile(outPath)
  // eslint-disable-next-line no-console
  console.log(`Generated ${outPath}`)
}

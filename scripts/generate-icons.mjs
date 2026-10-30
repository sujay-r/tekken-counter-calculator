#!/usr/bin/env node
/**
 * Generate the PWA icons (no image dependencies).
 *
 *   node scripts/generate-icons.mjs
 *
 * Writes web/public/icon-192.png, icon-512.png and apple-touch-icon.png.
 * The artwork is intentionally simple: three frame-data bars on a dark field.
 */
import { deflateSync } from 'node:zlib'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const OUT = resolve(ROOT, 'web/public')

const BG = [15, 23, 42]
const AMBER = [245, 165, 36]
const GREEN = [74, 222, 128]

const CRC_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let n = 0; n < 256; n += 1) {
    let c = n
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    table[n] = c >>> 0
  }
  return table
})()

function crc32(buffer) {
  let c = 0xffffffff
  for (const byte of buffer) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8)
  return (c ^ 0xffffffff) >>> 0
}

function chunk(type, data) {
  const length = Buffer.alloc(4)
  length.writeUInt32BE(data.length, 0)
  const typeBuffer = Buffer.from(type, 'ascii')
  const crc = Buffer.alloc(4)
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0)
  return Buffer.concat([length, typeBuffer, data, crc])
}

function encodePng(size, pixelAt) {
  const stride = size * 4 + 1
  const raw = Buffer.alloc(stride * size)
  for (let y = 0; y < size; y += 1) {
    raw[y * stride] = 0 // filter: none
    for (let x = 0; x < size; x += 1) {
      const [r, g, b] = pixelAt(x, y)
      const at = y * stride + 1 + x * 4
      raw[at] = r
      raw[at + 1] = g
      raw[at + 2] = b
      raw[at + 3] = 255
    }
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0)
  ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8 // bit depth
  ihdr[9] = 6 // RGBA
  ihdr[10] = 0
  ihdr[11] = 0
  ihdr[12] = 0
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

/** Bars are laid out in fractions of the icon so every size matches. */
const BARS = [
  { y: 0.34, w: 0.5, color: AMBER },
  { y: 0.46, w: 0.34, color: GREEN },
  { y: 0.58, w: 0.42, color: AMBER },
]
const BAR_HEIGHT = 0.08
const RADIUS = 0.04

function inRoundedRect(x, y, left, top, width, height, radius) {
  const right = left + width
  const bottom = top + height
  if (x < left || x > right || y < top || y > bottom) return false
  const cx = Math.min(Math.max(x, left + radius), right - radius)
  const cy = Math.min(Math.max(y, top + radius), bottom - radius)
  return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2 + 1e-9
}

function makeIcon(size) {
  const bars = BARS.map((bar) => ({
    left: (1 - bar.w) / 2,
    top: bar.y,
    width: bar.w,
    height: BAR_HEIGHT,
    color: bar.color,
  }))
  return encodePng(size, (x, y) => {
    const fx = (x + 0.5) / size
    const fy = (y + 0.5) / size
    for (const bar of bars) {
      if (
        inRoundedRect(
          fx,
          fy,
          bar.left,
          bar.top,
          bar.width,
          bar.height,
          Math.min(RADIUS, bar.height / 2),
        )
      ) {
        return bar.color
      }
    }
    return BG
  })
}

await mkdir(OUT, { recursive: true })
for (const [name, size] of [
  ['icon-192.png', 192],
  ['icon-512.png', 512],
  ['apple-touch-icon.png', 180],
]) {
  const png = makeIcon(size)
  await writeFile(resolve(OUT, name), png)
  console.log(`${name}: ${(png.length / 1024).toFixed(1)} KB`)
}

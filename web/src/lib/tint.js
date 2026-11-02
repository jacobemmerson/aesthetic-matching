/** A tint colour taken from the user's photos, the way Now Playing tints from album art. Hues are oklch degrees. */

const linear = (c) => { c /= 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4 }
const gamma = (c) => { c = Math.min(1, Math.max(0, c)); return c <= .0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - .055 }

/** sRGB bytes → oklab [L, a, b] (Björn Ottosson's matrices). */
export function oklab(r, g, b) {
  const [R, G, B] = [linear(r), linear(g), linear(b)]
  const l = Math.cbrt(.4122214708 * R + .5363325363 * G + .0514459929 * B)
  const m = Math.cbrt(.2119034982 * R + .6806995451 * G + .1073969566 * B)
  const s = Math.cbrt(.0883024619 * R + .2817188376 * G + .6299787005 * B)
  return [.2104542553 * l + .793617785 * m - .0040720468 * s, 1.9779984951 * l - 2.428592205 * m + .4505937099 * s, .0259040371 * l + .7827717662 * m - .808675766 * s]
}

/** oklab → linear sRGB (may leave [0, 1] when out of gamut). */
const rgbLinear = (L, a, b) => {
  const l = (L + .3963377774 * a + .2158037573 * b) ** 3
  const m = (L - .1055613458 * a - .0638541728 * b) ** 3
  const s = (L - .0894841775 * a - 1.291485548 * b) ** 3
  return [4.0767416621 * l - 3.3077115913 * m + .2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s, -.0041960863 * l - .7034186147 * m + 1.707614701 * s]
}

const MIN_CHROMA = .03  // below this a pixel is grey and says nothing about hue

/** Chroma-weighted circular mean hue of RGBA bytes, or null when nothing is colourful enough. */
export function dominantHue(rgba) {
  let x = 0, y = 0
  for (let i = 0; i + 3 < rgba.length; i += 4) {
    const [, a, b] = oklab(rgba[i], rgba[i + 1], rgba[i + 2])
    const c = Math.hypot(a, b)
    if (c < MIN_CHROMA) continue
    x += a; y += b   // summing the chroma vectors weights each pixel by its chroma
  }
  if (Math.hypot(x, y) < MIN_CHROMA) return null
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360
}

const TONE = { light: { L: .6, C: .2 }, dark: { L: .7, C: .18 } }  // fixed perceptual lightness, so every hue has the same contrast on its background

/** Hex tint for a hue in the given scheme, with chroma reduced until it fits sRGB. */
export function tintHex(hue, scheme = 'light') {
  const { L } = TONE[scheme]
  let { C } = TONE[scheme]
  const rad = (hue * Math.PI) / 180
  let rgb
  for (let i = 0; i < 12; i++) {
    rgb = rgbLinear(L, C * Math.cos(rad), C * Math.sin(rad))
    if (rgb.every((v) => v >= -.001 && v <= 1.001)) break
    C *= .85
  }
  return '#' + rgb.map((v) => Math.round(gamma(v) * 255).toString(16).padStart(2, '0')).join('')
}

const SAMPLE = 16  // px per side; enough for a hue, cheap to decode

/** Dominant hue across image files, or null if nothing can be decoded. Browser only. */
export async function hueOfFiles(files) {
  try {
    const canvas = new OffscreenCanvas(SAMPLE, SAMPLE)
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    const bytes = []
    for (const f of files) {
      const bmp = await createImageBitmap(f, { resizeWidth: SAMPLE, resizeHeight: SAMPLE })
      ctx.drawImage(bmp, 0, 0); bmp.close()
      bytes.push(...ctx.getImageData(0, 0, SAMPLE, SAMPLE).data)
    }
    return dominantHue(Uint8ClampedArray.from(bytes))
  } catch { return null }
}

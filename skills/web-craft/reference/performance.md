# Performance reference

Load this only when tuning speed or reviewing a slow page.

## Targets (Core Web Vitals, 75th percentile on mobile)
- LCP 2.5 s or less: the largest visible image or text block.
- INP 200 ms or less: response to taps and clicks.
- CLS 0.1 or less: layout must not jump.
Total page weight for a content page: aim under 500 KB before images, 1.5 MB with them.

## LCP
- Identify the LCP element (hero image or headline). Do not lazy-load it. Add `fetchpriority="high"`; for a CSS
  background hero, switch to an `<img>` so the browser discovers it early.
- Serve it at display size: `srcset` + `sizes`, AVIF or WebP with a JPEG fallback via `<picture>`.
- Keep the HTML small and the CSS for first paint inline (under ~10 KB); load the rest with `<link rel="stylesheet">`.
- `<link rel="preconnect">` only for origins used above the fold (fonts, image CDN). Not for everything.

## CLS
- `width` and `height` attributes on every `<img>`/`<video>`, or CSS `aspect-ratio`.
- Reserve space for embeds, ads, banners and late-loaded content.
- Fonts: `font-display: swap` plus `size-adjust` fallback metrics, or a system stack.

## INP and JavaScript
- Ship less JS: if a feature is CSS (`:hover`, `<details>`, `scroll-behavior`, `position: sticky`, `:has()`), use CSS.
- `defer` all scripts; split long tasks; debounce scroll/resize handlers; use passive listeners; use
  `IntersectionObserver` instead of scroll polling.
- Third-party scripts (analytics, chat, tags) load after the page is interactive, one at a time, each justified.

## Images and media
- SVG for logos, icons, simple illustrations; inline only if tiny and used once.
- Compress: photos 70-80 quality WebP/AVIF. Video: `preload="none"` with a poster; no autoplay with sound.
- Never ship originals from a camera or design export.

## Fonts
- One or two families, only the weights used (usually 400 and 700), WOFF2, self-hosted when possible, subset to the
  needed language. A variable font replaces several static files.

## CSS
- Avoid deep selectors and huge unused frameworks; remove unused CSS before shipping.
- Animate `transform`/`opacity`; use `will-change` sparingly; `content-visibility: auto` for long off-screen sections.

## Caching and delivery (when you control hosting)
- Hashed asset filenames with `Cache-Control: max-age=31536000, immutable`; HTML revalidated.
- Brotli or gzip on text assets; HTTP/2 or 3; a CDN for static files.

## Measuring
- Lighthouse / PageSpeed Insights for lab numbers; real-user data (CrUX) is the truth. Say which you used, and say
  plainly when numbers were not measured.

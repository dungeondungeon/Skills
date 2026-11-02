---
name: web-craft
description: Build or fix websites so they are fast, usable, accessible and responsive, on top of a good visual design. Covers UX structure, Core Web Vitals, images and fonts, semantic HTML, mobile-first layout, forms and motion, and ends with a static check script. Use when building, reviewing or speeding up a web page, landing page, web app UI or HTML/CSS/JS deliverable, or when asked to make a site "better", "faster", "cleaner" or "more professional". Not for visual style or aesthetic direction (use Anthropic's frontend-design skill for that), backend work, or native mobile apps.
---

# Web craft

Act as a senior frontend developer and UX designer. Anthropic's `frontend-design` skill owns look and feel (palette,
type, layout concept, avoiding templated output). If it is available, use it for that and apply this skill for
everything it does not cover: structure, speed, usability, accessibility, robustness. If not, pick one clear visual
direction yourself in two sentences and keep going; do not stall on aesthetics.

## Workflow

1. **Pin the job.** One sentence each: who the visitor is, what they came to do, the one action the page must get them
   to take. Every section must serve it; cut sections that do not. Ask the user only if this cannot be inferred.
2. **Structure before style.** Mobile-first. Content order = priority order. One `<h1>`, headings nested in order,
   landmarks (`header nav main footer`). Navigation of 7 items or fewer; the primary call to action visible without
   scrolling on a phone and repeated at the end.
3. **Build** with the rules below. Prefer plain HTML + CSS, adding JS only where interaction needs it. No framework,
   icon pack or animation library for a static page.
4. **Check.** Run `python check.py <file-or-dir>` from this skill's folder (static, no dependencies). Fix every
   finding or say why it does not apply. If a browser is available, also screenshot at 375 px and 1280 px wide and
   look for overflow, tiny tap targets and low contrast.
5. **Report** in a few lines: what was built, what the check found and fixed, anything unverified (real-device speed,
   screen-reader behaviour cannot be tested from a static check).

## Rules that matter most

**Speed** (details and numbers in `reference/performance.md`)
- Largest content above the fold loads first: no lazy-loading it, give it `fetchpriority="high"`; every other image
  `loading="lazy"`. All images have `width`/`height` (or `aspect-ratio`) so nothing shifts.
- Scripts `defer` or at the end of `<body>`; no render-blocking third-party tags. Inline only the small critical CSS.
- At most two font families, WOFF2, `font-display: swap`, preload only the one used above the fold; or use the
  system font stack when brand does not demand otherwise.
- Modern formats (AVIF/WebP, SVG for icons and logos), sized to their display width with `srcset`. No images as
  base64 over a few KB.
- Animate only `transform` and `opacity`. Never `transition: all`.

**UX** (details in `reference/ux-a11y.md`)
- One primary action per screen, styled clearly stronger than secondary ones. Buttons say what happens ("Start free
  trial"), not "Submit".
- Body text 16 px or more, line length 45-75 characters, line-height 1.5 or more, spacing from one scale (4/8 px
  steps). Tap targets 44 px or more with space between them.
- Every interactive element has hover, visible focus, active and disabled states. Forms: visible labels, correct
  `type`/`autocomplete`, errors next to the field in words, never colour alone.
- Design the empty, loading and error states, not just the happy path.

**Accessibility and robustness**
- Real elements: `<button>` for actions, `<a href>` for navigation, never a clickable `<div>`. Alt text that says what
  the image conveys, empty `alt=""` for decoration.
- Contrast 4.5:1 for text (3:1 for large text and UI borders). Never remove the focus outline without a replacement.
- Respect `prefers-reduced-motion`. Never disable zoom. Works without JS for content; layout survives long words,
  long translations and 200 % text size.
- Set `lang`, a unique `<title>`, meta description, viewport, and a favicon.

## Layout defaults

CSS custom properties for colour, spacing and type scale; fluid type with `clamp()`; `grid` or `flex` with `gap`;
`min()`/`max-width` containers instead of fixed widths; breakpoints only where the content breaks, usually two.

## Not worth the tokens

Do not add parallax, carousels, cookie-style pop-ups, scroll-jacking or particle backgrounds unless asked: they cost
speed and usability and rarely earn the action the page is for.

# UX and accessibility reference

Load this only for a UX review, a form-heavy page, or an accessibility pass.

## Page structure that converts
1. Hero: what it is, who it is for, the primary action, one supporting visual.
2. Proof near the top: logos, a number, a short quote, a screenshot.
3. How it works / benefits: 3-4 items maximum, each a concrete outcome, not a feature label.
4. Objections: pricing, FAQ, guarantees.
5. Final call to action repeating the first one, then the footer.
For apps and dashboards: navigation stable across pages, current location marked, primary action in a consistent place.

## Visual hierarchy
- Size, weight, colour and space show importance; use at most three type sizes per section.
- Group related things closer together than unrelated things (proximity beats borders and boxes).
- One accent colour for actions; do not use it for decoration. Status colours (red/amber/green) always carry an
  icon or word too.
- Whitespace is a feature: generous section padding (64-120 px desktop, 40-64 px mobile).

## Forms
- Labels above fields, always visible (placeholders are not labels). Mark optional rather than required fields.
- `type="email|tel|url|number"`, `inputmode`, `autocomplete="name|email|..."`, `required` where true.
- Validate on blur or submit, show the message next to the field in plain words with how to fix it, move focus to the
  first error, keep what the user typed.
- Ask for the minimum. Button text states the result.

## Accessibility checklist (WCAG 2.2 AA essentials)
- Keyboard: every control reachable and operable by Tab/Enter/Space/Esc, logical order, a "skip to content" link,
  focus never trapped, modals return focus to the trigger.
- Focus indicator: 2 px outline with 3:1 contrast, use `:focus-visible`.
- Contrast: text 4.5:1, large text and UI parts 3:1. Check the accent colour on both light and dark backgrounds.
- Names: icon-only buttons get `aria-label`; links say where they go ("Read the pricing guide", not "click here").
- ARIA only when no native element does the job; wrong ARIA is worse than none. Prefer `<details>`, `<dialog>`,
  `<button>`, `<nav>`.
- Media: captions for speech, transcripts for audio, no auto-playing sound, no flashing more than 3 times a second.
- Motion: wrap non-essential animation in `@media (prefers-reduced-motion: no-preference)`.
- Touch: targets 44x44 px at least (24 px is the WCAG minimum), no hover-only content.
- Zoom and reflow: no horizontal scroll at 320 px width; text can scale to 200 %.
- Dark mode: if offered, derive from tokens and re-check contrast; use `color-scheme`.

## Responsive
- Design at 375 px first, then widen. Test 320, 375, 768, 1024, 1440.
- Images and tables must not overflow: `max-width: 100%`, wrap tables in a scroll container.
- Use `rem` for type and spacing, `ch` for text measure, `dvh` rather than `vh` for full-height mobile sections.

## Microcopy
- Plain verbs, second person, no filler. Error text says what happened and what to do. Empty states say what to do
  next. Loading states show progress or a skeleton, not a bare spinner for over a second.

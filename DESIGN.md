---
version: alpha
name: ComplaintIQ
description: "Warm editorial support-software look, adapted from the Intercom analysis in VoltAgent/awesome-design-md: a cream canvas, white cards lifted on hairlines, charcoal type and buttons, and one orange accent kept for the AI's own marks."

colors:
  canvas: "#f5f1ec"
  surface-1: "#ffffff"
  surface-2: "#ebe7e1"
  hairline: "#d3cec6"
  hairline-soft: "#ebe7e1"
  ink: "#111111"
  ink-muted: "#626260"
  ink-subtle: "#7b7b78"
  on-primary: "#ffffff"
  primary: "#111111"
  inverse-canvas: "#000000"
  inverse-ink: "#ffffff"
  inverse-ink-muted: "#9c9fa5"
  ai-accent: "#e8590c"
  error: "#c41c1c"
  success: "#0f9d58"
  chart-blue: "#65b5ff"
  chart-cyan: "#03b2cb"
  chart-lime: "#9cc417"
  chart-green: "#0bb04a"
  chart-pink: "#ff2067"
  chart-orange: "#fe7a2f"

typography:
  family: "Geist (text and display), Geist Mono (product UI only)"
  display-xl: { size: 72px, weight: 500, lineHeight: 1.05, tracking: -0.03em }
  display-lg: { size: 56px, weight: 500, lineHeight: 1.10, tracking: -0.025em }
  display-md: { size: 40px, weight: 500, lineHeight: 1.15, tracking: -0.02em }
  headline:   { size: 28px, weight: 500, lineHeight: 1.20 }
  card-title: { size: 22px, weight: 500, lineHeight: 1.25 }
  body-lg:    { size: 18px, weight: 400, lineHeight: 1.50 }
  body:       { size: 16px, weight: 400, lineHeight: 1.50 }
  body-sm:    { size: 14px, weight: 400, lineHeight: 1.50 }
  button:     { size: 15px, weight: 500 }

rounded: { xs: 4px, sm: 6px, md: 8px, lg: 12px, xl: 16px, pill: 9999px }
spacing: { xxs: 4px, xs: 8px, sm: 12px, md: 16px, lg: 24px, xl: 32px, xxl: 48px, section: 96px }
---

## Rules

- **Canvas is cream** (`canvas`), never pure white. Cards lift onto `surface-1` white with a 1px `hairline` border. That surface change is the only depth: no drop shadows, no gradients, no glows.
- **Charcoal is the primary.** Headlines, body and the primary button (`primary`, 8px radius, 10px 18px padding) are charcoal. Secondary buttons are white with a hairline border. No pill buttons.
- **One orange, for the AI only.** `ai-accent` marks what the model did: the agent avatar, a predicted value, a drafted line. It is never a button, a section ground or a decoration.
- **One family.** Geist at 500 for display with negative tracking, 400 for body. Geist Mono only inside product UI (IDs, code). Sentence case everywhere, no tracked capitals.
- **Radii:** 8px buttons and inputs, 12px cards, 16px product mock-ups, pill only for tabs and avatars.
- **The product leads.** Every section's picture is the ComplaintIQ console or one of its panels, framed in a white 16px tile.
- **Charts** use the chart palette inside the product only. It never becomes a brand surface.
- **Inverse** (`inverse-canvas` black) is used once a page at most, for a single proof band.

## Where it is applied

- Landing page: `frontend/index.html` (tokens in its `:root` block, on the taste-skill kit in `frontend/public/assets`).
- Console: `frontend/src/index.css` (`@theme`) and `frontend/src/ui.jsx` (category colours, buttons, cards).

# Login Hero Refresh Design

## Context
- Current login split layout introduces ICS branding but the hero tile feels flat and low-fidelity per stakeholder feedback.
- Goal: replace the small tile with a full-width hero strip that highlights the ICS logo, tagline, and reliability cues while adding a footer credit line.
- Constraints: keep existing authentication logic untouched; ensure the new visual treatment remains responsive for mobile breakpoints.

## Layout Overview
- Preserve two-column structure (≈55% hero / 45% form on desktop).
- Hero strip dimensions ~320×96px, positioned near the top-left of the hero panel with consistent horizontal padding; supporting copy and stat card align in a single vertical stack beneath it.
- Footer area within hero panel now contains `Made by Bagus Ganteng 😎`, anchored bottom-left on desktop and centered below hero content on mobile.

## Visual System
- Background: deep navy gradient (`#071530 → #051737 → #081d3b`) with large blurred radial highlight centered behind the hero strip to create focus.
- Hero strip: frosted glass pill, gradient fill from `rgba(255,255,255,0.18)` to `rgba(255,255,255,0.04)`, border `rgba(255,255,255,0.3)`, outer glow `rgba(127,196,255,0.25)`, subtle noise overlay.
- Logo: existing PNG sits inside a white inset capsule with 10px padding and a gentle drop shadow to keep edges crisp.
- Divider: slim frosted divider between logo area and copy using `border-white/30`.
- Typography: uppercase label (`letter-spacing 0.55em`, `rgba(255,255,255,0.65)`), headline `Infrastructure Command Suite` in `font-semibold` with slight text glow; supporting copy in `text-slate-300`. Updated copy emphasizes operational visibility, compliance alerts, and twice-daily digests.
- Stat card: horizontal glass strip mirroring hero styling; displays uptime metrics and refresh cadence.
- Footer text: `Made by Bagus Ganteng 😎` in small caps/light weight, matching muted foreground color.

## Responsiveness
- On mobile, hero panel stacks atop form; hero strip stretches to full width within padding, logo scales down proportionally, and supporting copy/stat card follow with tightened spacing.
- Footer credit moves beneath hero content, centered to maintain balance; ensure sufficient margin so it does not crowd form section when stacked.

## Testing / Validation Notes
- Visual QA across desktop (≥1024px) and mobile (≤640px) to ensure gradients, glow effects, and footer placement render correctly.
- Accessibility check: maintain contrast ratios for text on gradients; ensure footer emoji/text remain legible.
- No functional auth changes; existing tests remain valid after layout updates.

## Verification Log
- 2026-03-27: Launched `npm run dev` (Next.js auto-switched to port 3001) to confirm the refreshed hero page renders without build/runtime errors. Full visual check will be completed in-browser when a GUI is available.

# Hub_ML Design Spec

Reference files read:
- `design-reference/extracted/Home.dc.html`
- `design-reference/extracted/Hub_ML System.dc.html`
- `design-reference/extracted/Mentor Task.dc.html`
- `design-reference/extracted/Theory Quality.dc.html`
- `design-reference/Hub_ML System.html`
- `design-reference/Theory Quality.html`
- `design-reference/Hub_ML_Home.pptx`

## Visual Direction

Dark engineering console for a local-first workstation. The interface is restrained, high contrast, dense, and task-oriented. Avoid decorative gradients, large shadows, marketing hero layouts, card-in-card structures, and random Tailwind colors.

## Colors

| Token | Value |
|---|---|
| bg | `#0A0C11` |
| surface | `#12151D` |
| raised | `#1A1F29` |
| border | `#313A48` |
| borderStrong | `#3D4757` |
| accent | `#8B9BFF` |
| accentSoft | `rgba(139,155,255,.14)` |
| text | `#F1F3F8` |
| dim | `#AAB3C2` |
| faint | `#6A7382` |
| pass | `#4FD06A` |
| warn | `#E5B23A` |
| fail | `#FF5E54` |
| ready | `#5FAEFF` |

Secondary colors observed in panels/code/skeletons: `#0B0E14`, `#0F1219`, `#1d2330`, `#242a37`, `rgba(10,12,17,.82)`, `rgba(10,12,17,.86)`, `rgba(139,155,255,.28)`, `rgba(79,208,106,.14)`, `rgba(229,178,58,.14)`, `rgba(95,174,255,.14)`.

## Fonts

- display: `Space Grotesk`
- ui: `IBM Plex Sans`
- mono/meta/code: `IBM Plex Mono`

Weights observed: `400`, `500`, `600`, `700` for display; `400`, `500`, `600` for UI and mono.

## Layout

- body background: `#0A0C11`
- home-like max-width: `760px`
- system/reference max-width: `1120px`
- page padding: `40px 28px`
- compact section gap: `32px`
- relaxed section gap: `46px`
- top bar height: `44px`
- bottom status bar height: `34px`
- main content is centered; shell remains full-height dark.
- common grids: `repeat(4,1fr)`, `repeat(2,1fr)`, `1fr 1fr`, `1.4fr 1fr`.

## Radius

- card radius: `12px`
- small radius: `8px`
- pill radius: `999px`
- tiny marker radius: `2px`
- skeleton micro radius: `5px` or `6px`

## Borders

- default border: `1px solid #313A48`
- hover border: `#3D4757`
- fail accent: `2px solid #FF5E54` on left border

## Motion

```css
@keyframes hubFadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: none; }
}

@keyframes hubSpin {
  to { transform: rotate(360deg); }
}

@keyframes hubShimmer {
  0% { background-position: -180% 0; }
  100% { background-position: 180% 0; }
}

@keyframes hubPulse {
  0% { box-shadow: 0 0 0 0 rgba(229,178,58,.45); }
  70% { box-shadow: 0 0 0 6px rgba(229,178,58,0); }
  100% { box-shadow: 0 0 0 0 rgba(229,178,58,0); }
}

@keyframes hubPulseGreen {
  0% { box-shadow: 0 0 0 0 rgba(79,208,106,.4); }
  70% { box-shadow: 0 0 0 6px rgba(79,208,106,0); }
  100% { box-shadow: 0 0 0 0 rgba(79,208,106,0); }
}

@keyframes hubRing {
  from { stroke-dashoffset: 213.6; }
  to { stroke-dashoffset: 0; }
}

@keyframes hubBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: .25; }
}

@keyframes hubBar {
  from { width: 0; }
}

@keyframes hubExpand {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: none; }
}
```

Transitions:
- hover transform: `translateY(-2px)`
- duration: `160ms`
- easing: `cubic-bezier(.2,.7,.3,1)`
- reduced motion fallback sets animation duration, iteration count, and transition duration to near-zero.

## Components

### AppShell

Dark full-height layout with centered main content, sticky `TopIdeBar`, sticky `BottomStatusBar`, and no decorative background beyond the solid `#0A0C11` field.

### TopIdeBar

- sticky top `0`
- z-index `20`
- height `44px`
- padding `0 22px`
- background `rgba(10,12,17,.82)`
- `backdrop-filter: blur(10px)`
- bottom border `1px solid #313A48`
- mono font `12.5px`
- left breadcrumb with 8x8 square accent dot, radius `2px`, `box-shadow: 0 0 8px var(--hub-accent-soft)`
- right command palette pill

### BottomStatusBar

- sticky bottom `0`
- height `34px`
- padding `0 18px`
- background `rgba(10,12,17,.86)`
- `backdrop-filter: blur(10px)`
- top border `1px solid #313A48`
- mono font `11.5px`
- color `#6A7382`
- left status group, right branch/shortcut group

### StatusChip

- `inline-flex`
- align center
- gap `7px` or `8px`
- padding `3px 9px`, `4px 10px`, or `6px 13px`
- border-radius `999px`
- border `1px solid #313A48`
- background `#1A1F29`
- font `IBM Plex Mono`
- dot size `6px` or `7px`
- variants: `PASS`, `FAIL`, `ERROR`, `IN PROGRESS`, `READY`, `DONE`
- live states may pulse

### MetricTile

- surface card, border `#313A48`
- radius `12px`
- equal min-height
- big `Space Grotesk` number
- mono label/meta
- optional muted `/total`
- optional progress bar only for real ratios

### ClickableCard

- whole card clickable
- display flex
- justify-content space-between
- gap `16px`
- border `1px solid #313A48`
- border-radius `12px`
- padding `16px 20px` or `18px 20px`
- background `#12151D`
- transition `transform 160ms cubic-bezier(.2,.7,.3,1), border-color 160ms cubic-bezier(.2,.7,.3,1)`
- hover `translateY(-2px)`
- hover border `#3D4757`
- arrow default `#6A7382`, hover `#8B9BFF`
- fail variant has `2px` left border `#FF5E54`

### SectionHeader

- flat, not inside a card
- mono uppercase eyebrow
- `Space Grotesk` title
- optional chip
- one-line description
- no card-in-card

### Skeleton

- shimmer gradient `linear-gradient(90deg,#12151D 25%,#1d2330 50%,#12151D 75%)`
- background-size `200% 100%`
- animation `hubShimmer 1.5s linear infinite`

### QualityGateCard

- ring/percentage visual, `100%` in Home reference
- label `QUALITY GATE` or product equivalent
- status chip
- count with muted `/total`
- short caption

### EmptyState

- compact surface card
- one icon/marker
- one line of explanation
- one primary action when needed

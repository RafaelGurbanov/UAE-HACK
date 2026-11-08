# Design reference: tokens (from the project owner)

The single-file prototype (`policy-command-centre.html`) is not available. These tokens are the design reference instead. Implemented in `frontend/src/styles/tokens.css`.

## Dark theme (default)
| Token | Value |
|---|---|
| `--bg` | `#070b14` |
| `--bg2` | `#0d1424` |
| `--card` | `rgba(255,255,255,.05)` |
| `--line` | `rgba(255,255,255,.12)` |
| `--tx` | `#ece6d8` |
| `--mut` | `#9aa3b5` |
| `--gold` | `#e8b04a` |
| `--teal` | `#3dd6c3` |
| `--vio` | `#8b7bff` |
| `--red` | `#ff6b5e` |
| `--amb` | `#f2b34a` |
| `--blu` | `#5aa2ff` |

## Light theme
| Token | Value |
|---|---|
| `--bg` | `#f6f2e9` |
| `--bg2` | `#ebe5d6` |
| `--card` | `rgba(255,255,255,.7)` |
| `--line` | `rgba(20,30,50,.14)` |
| `--tx` | `#1a2133` |
| `--mut` | `#5b6478` |
| `--gold` | `#9a6a10` |
| `--teal` | `#0b8a7b` |
| `--vio` | `#5a49d6` |
| `--red` | `#c93a2c` |
| `--amb` | `#a86d00` |
| `--blu` | `#2a6fd0` |

## Background
Radial gradients:
- violet, top-left, about 28% mix
- teal, top-right, 22%
- gold, bottom, 20%

## Type
- **Fraunces 700:** headings.
- **Instrument Sans:** body.
- **Monospace:** logs only.

## Shapes
- **Cards:** radius 18px, 1px `--line` border, backdrop blur.
- **Pills:** radius 99px.
- **Primary button:** gold with dark text.
- **Search bar:** violet glow ring.

## Severity
Blue (calm), amber (concern), red (escalation): `--blu`, `--amb`, `--red`.

## Pipeline map
- 7 circular nodes (SRC, C, PP, M, P, D, SINK), joined by a line carrying an animated teal pulse.
- A lit node has a gold border, a gold-tinted fill and a glow.

## Layout
- Sticky top nav: Legal search, Scenario room, Gap board, Audit trail, theme toggle.
- Content max width 1080px.
- Hero headline: "Ask the law. See the source."

## Implementation notes
- **Light-theme primary button:** the light `--gold` (`#9a6a10`) with dark text is only about 3.5:1, which fails WCAG AA. The light-theme button therefore uses `--gold-btn: #e8b04a` (the dark-theme gold) behind dark text, at about 9:1. Light `--gold` is still used for text accents and borders.
- **Extra navigation:** Laws and About are required routes but aren't in the nav list above, so they're linked from the footer. The EN/AR language toggle sits beside the theme toggle.
- **Light-theme text variants:** for small text, light-theme teal, gold, amber and blue fall below 4.5:1 on `--bg`/`--bg2` (3.8–4.4). `*-ink` variants fix this:
  - `--teal-ink #097266`, `--gold-ink #875d0e`, `--amb-ink #8d5b00`, `--blu-ink #2563bb`, `--red-ink #ba3528`.
  - Each is at least 4.6:1 on both `--bg` and `--bg2`.
  - The original values still drive borders, fills, glows and icons.
  - In the dark theme, `*-ink` equals the base token (all are at least 7:1).

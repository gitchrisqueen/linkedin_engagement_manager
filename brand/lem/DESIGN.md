---
name: lem
status: draft for brand-owner review
source: "logo/06 Color Palette/LEM_Brand_Palette.txt (official palette sampled from the approved baseline) and logo/07 Reference"
colors:
  light:
    background: "#F9F9F9"   # official light background
    surface: "#FFFFFF"      # official white
    text: "#1F2C37"         # official primary charcoal
    muted: "#5B6670"        # proposed: charcoal tint for secondary text
    primary: "#054DB1"      # official primary blue: buttons and links
    on-primary: "#FFFFFF"
    hairline: "#D7DCE1"     # proposed: decorative dividers only
    field-border: "#7A8590" # proposed: input and control boundaries
  dark:
    background: "#111A22"   # proposed: deepened charcoal
    surface: "#1F2C37"      # official charcoal as raised surface
    text: "#E8EDF2"
    muted: "#A3AEB8"
    primary: "#7FB0FF"      # proposed: lifted blue, dark text on it
    on-primary: "#111A22"
    hairline: "#33414D"
    field-border: "#7B8894"
typography:
  display: { family: "Inter (display sizes)", weights: [600], licence: "OFL-1.1", note: "the same InterVariable file at display sizes, -0.02em tracking; Inter Tight has no official woff2, so it is not shipped" }
  body: { family: "Inter", weights: [400, 600], licence: "OFL-1.1" }
  scale: [13, 16, 20, 25, 31, 39, 49]   # px; ratio 1.25 from a 16 px body
  body_px: { desktop: 17, phone: 16 }
  measure_chars: [45, 75]
spacing: [4, 8, 16, 24, 32, 48, 64, 96]
grid: { desktop_columns: 12, phone_columns: 4, content_max_rem: 72, gutter_px: 16 }
radius: { control: 6, card: 10 }
elevation: { card: "0 1px 2px rgba(31,44,55,.08)" }
motion: { reduce: respect }
targets: { min_px: 44 }
---

## Rationale
- Blue and charcoal are the approved LEM marks (the logo baselines in `logo/07 Reference`). Blue carries action and links; charcoal carries text. The light background is the official #F9F9F9, so pages sit on the same ground as the logo proof sheet.
- Dark theme: the brand blue is too dark to read on charcoal, so the dark primary is a lifted blue (#7FB0FF) with dark text on it, and the official charcoal becomes the raised surface. Brand owner to confirm.
- Type: one OFL family, Inter, self-hosted as the official variable woff2, for body and display alike (display = Inter at display sizes, weight 600, -0.02em tracking). One file serves both roles, so marketing pages and the app read as one product. The app still uses the system stack until its own design pass.
- The one bold element on a LEM page: the product itself, in a real screenshot of the app (owned asset), not an illustration.

## Contrast (WCAG 2.2 AA; computed 2026-10-16)

| Theme | Pair | Ratio |
|---|---|---|
| light | text #1F2C37 on background #F9F9F9 | 13.53 |
| light | muted #5B6670 on background | 5.57 |
| light | on-primary #FFFFFF on primary #054DB1 | 7.77 |
| light | primary #054DB1 (links) on background | 7.38 |
| dark | text #E8EDF2 on background #111A22 | 14.92 |
| dark | muted #A3AEB8 on background | 7.79 |
| dark | on-primary #111A22 on primary #7FB0FF | 8.00 |
| light | text #1F2C37 on surface #FFFFFF | 14.25 |
| light | muted #5B6670 on surface #FFFFFF | 5.87 |
| light | field-border #7A8590 on background #F9F9F9 | 3.57 (control boundary, 3:1 needed) |
| light | field-border #7A8590 on surface #FFFFFF | 3.76 (control boundary) |
| dark | text #E8EDF2 on surface #1F2C37 | 12.10 |
| dark | muted #A3AEB8 on surface #1F2C37 | 6.31 |
| dark | primary/link #7FB0FF on background #111A22 | 8.00 |
| dark | primary/link #7FB0FF on surface #1F2C37 | 6.48 |
| dark | field-border #7B8894 on background #111A22 | 4.85 (control boundary) |
| dark | field-border #7B8894 on surface #1F2C37 | 3.93 (control boundary) |

# Part 2 dashboard shell — design direction

This folder ships **static HTML mocks** under [`designs/`](designs/index.html) (three original directions + **one hybrid jury shell**). Pick one as the primary Streamlit skin (custom CSS + layout), or tweak from the hybrid.

## Recommendation (hackathon default)

**Primary for jury / pitch: Hybrid — clarté + élégance** ([`designs/design-hybrid-clarte-elegance.html`](designs/design-hybrid-clarte-elegance.html))

- Keeps Design **1** strengths: full **STEG dual ledgers**, gas table + normalization ladder, **SONEDE** amounts + split bar, **SCADA** as readable pull-quote lines (not only a ticker).
- Adopts Design **2** strengths: **warm sand field**, Fraunces + Newsreader masthead, light panels, generous spacing — avoids the “full-screen terminal” first impression.
- **Right rail (ink)** is explicitly **télémesure edge only** so judges never confuse MQTT with bill extraction.

**Alternate (operator-dense): Design 1 — Salle des machines** ([`designs/design-1-salle-des-machines.html`](designs/design-1-salle-des-machines.html))

- Single dark HMI: maximum density for team debugging; less ideal as first visual in a jury walkthrough unless paired with verbal context.

**Choose Design 2 — Relevé ouvert** if the pitch prioritizes **narrative / print** (audit storytelling, large numerals, magazine fold).

**Choose Design 3 — Chronologie unifiée** if the pitch prioritizes **merge-layer** clarity (bill periods + IoT aggregates on one spine).

## Other hybrids (allowed)

- Design 1 center + Design 2 right rail for live JSON transcript (similar to shipped hybrid).
- Design 3 timeline + Design 1 oscillograph footer.

## Palette (all mocks)

| Token   | HEX       |
|---------|-----------|
| Sand    | `#BBAB8C` |
| Umber   | `#776B5D` |
| Ink     | `#282A3A` |

No purple accents. Neutrals: black/white and alpha mixes of the three colors only.

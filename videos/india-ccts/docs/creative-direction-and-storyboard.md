# India's CCTS explainer: creative direction, storyboard and visual plan

## 1. Concept
**"Carbon becomes a line item."** The film opens on two identical cement plants at night. One modernises and one doesn't, and the scheme turns that choice into money. From there it moves from intuition (a fitness-target analogy) to vocabulary, history, mechanism, a worked example, a dated status snapshot, opportunities, critiques and outlook. It closes on what Indian businesses should do now.

**Tone.** A confident Indian business professional explaining an important development to peers: calm, precise, never promotional. The critiques chapter gives independent voices (IEEFA, CEEW) real space.

**Running time.** Roughly 15–16 minutes across 12 chapters (set by the generated narration).

## 2. Visual language
| Element | Treatment |
|---|---|
| Palette | ReGeneva Green `#20C997`, black `#000`, white `#FFF`. Supporting tints `#6FE3BF`, `#E6F9F2` and shades `#0E8F6A`, `#064E3B`. Coral `#FF6B57` only for "shortfall/cost" and amber `#F4B740` only for "draft/pending/illustrative" labels |
| Rhythm | Black cinematic chapters (story, mechanism, status, critique) alternate with white information chapters (concepts, data, opportunities) |
| Type | Encode Sans Condensed for headlines and numbers, Roboto for body. Tabular figures for data |
| Motion | Every element enters on a narration cue (synced to the voice). Kinetic typography, counters, drawn lines, a camera pan along the timeline, horizontal wipe transitions with a green leading edge, numbered chapter cards |
| Texture | Procedural night skyline with drifting smoke, a perspective data grid and particles in dark chapters, soft contour lines in light chapters, film grain and vignette |
| Honesty markers | "HYPOTHETICAL" / "ILLUSTRATIVE" tags. Status pills (NOTIFIED / LIVE / PUBLISHED / DRAFT / PENDING). A dated snapshot. Source footnotes on every chapter |
| Maps | Deliberately none, to avoid the legal risk of depicting India's boundaries |
| Branding | ReGeneva logo small in the corner (switching between dark and light versions), the title card, and the end card with tagline and call to action |

## 3. Chapter storyboard
| # | Chapter | Tone | Visual beats (each line = one cue) | Key on-screen data | Evidence |
|---|---|---|---|---|---|
| 0 | Two plants, one decision | Dark | Night skyline with Plants A & B and smoke → "Same size / product / market" → upgrade chips on A while A's smoke thins → energy-bill bars → "+CCC" vs "−CCC" cards → balance-sheet ledger with a new "Carbon" line → title card | none | narrative |
| 1 | The big picture | Light | CCTS node splits into Compliance (mandatory) and Offset (voluntary) branches → merge into "Carbon Credit Certificates" → fitness-target track (beat it / miss it) | none | E1–E3 |
| 2 | Decoding the jargon | Light | Glossary rail with 9 terms, highlight follows the voice. Term cards with mini-visuals: molecules, CO₂e conversion, intensity fraction, baseline/target bars (illustrative), CCC certificate, compliance vs voluntary, obligated vs non-obligated, the MRV loop, units table (ESCert / REC / CCC) | 1 CCC = 1 tCO₂e · 1 ESCert = 1 toe · 1 REC = 1 MWh | E5, E18, E19 |
| 3 | How India got here | Dark | Camera pans along a glowing timeline: 2010 REC → 2012 PAT → PAT Cycle I stats (counters) → 2017 ESCerts → Dec 2022 Amendment Act → 28 Jun 2023 CCTS → Dec 2023 offsets → "Energy → Emissions" comparison | 478 plants · 8 sectors · 8.67 Mtoe · ~30% above target | E1–E3, E18, E19 |
| 4 | Why India needs CCTS | Light | 2,959 MtCO₂e counter + sector stacked bar → NDC goal cards (45% by 2030, net zero 2070, 47% by 2035) → "efficiency + signal" → CBAM border graphic | 75.66% energy, 8.06% IPPU, 13.72% agriculture, 2.56% waste | E20–E22, E26 |
| 5 | How CCTS works | Dark | Org chart drawn line by line (NSC-ICM → BEE, MoEFCC, Grid-India, CERC) → five-step compliance pipeline with a travelling light | 2023-24 baseline | E4, E6, E13 |
| 6 | A worked example | Light | Two plant cards with intensity gauges against a dashed 0.80 target → formulas → results count up → penalty bar → caveat chips | 0.77 → 30,000 CCC · 0.82 → 20,000 CCC (hypothetical) | E7, E10, E11 |
| 7 | Where CCTS stands today | Dark | Three-panel dashboard dated 31 Oct 2026: entities (282 → 490), infrastructure checklist, "not yet confirmed" panel | 282, +208, 490 · FY2025-26 & 2026-27 · iron & steel DRAFT · no price | E7–E9, E13–E17 |
| 8 | Business opportunities | Light | Seven stakeholder tiles appear one per line, each tagged ESTABLISHED / EMERGING / GROWING / INDIRECT | none | analysis |
| 9 | Challenges & critiques | Dark | Illustrative chart (production ↑, intensity ↓, total emissions ↑) + five numbered critiques with attribution → "Credibility will be earned tonne by tonne" | IEEFA ~3% | E23–E25 |
| 10 | What comes next | Light | "Expected soon" (solid black) vs "Possible over time" (dashed) → "Sustainability report → Operating plan" | none | E9, E17 |
| 11 | What it means for you | Dark | Summary lines → "Get ready now" 01/02/03 → ReGeneva end card, follow CTA, sources and disclaimer | none | all |

## 4. Sound design
- **Voice:** Surya's Clone Voice (see `voice/surya-clone-voice.json`). High-pass, light compression and presence EQ. Always the loudest element.
- **Score:** original and synthesised, at 96 BPM.
  - Dark tension (sub drone, heartbeat, ticks, bell motif) for the hook and dark chapters.
  - An optimistic plucked pulse for light chapters.
  - A lifted progression for the close.
- **Mix:** the music is side-chain ducked under the voice.
- **Effects:** a riser before each chapter wipe and a low impact on each chapter card. A bigger riser and impact at the title reveal.
- **Mastering:** −14 LUFS integrated, −1.5 dBTP.

## 5. Accessibility
- An English `.srt` that matches the narration wording. It isn't burned in, so it never covers data.
- On-screen text stays short. No paragraph is longer than about 25 words.
- The light/dark contrast meets WCAG AA for body text.

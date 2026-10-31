# Final QA report: India's CCTS explainer (31 Oct 2026)

## Deliverables (verified)
| File | Spec | Check |
|---|---|---|
| `india-ccts-explainer-4k.mp4` | H.264 High, 3840×2160, 30 fps, AAC 320 kbps 48 kHz stereo, 12:53.8, 540 MB | 23,185/23,185 video frames · −14.0 LUFS · −1.4 dBTP |
| `india-ccts-explainer-1080p.mp4` | H.264 High, 1920×1080 (Lanczos downscale of the 4K master), 30 fps, AAC 320 kbps, 181 MB | 23,185 frames · −14.0 LUFS · −1.4 dBTP |
| `india-ccts-captions-en.srt` | English, matches the narration wording, ≤80 characters per cue | timed from the final narration |
| `india-ccts-chapters.txt` | 12 YouTube chapters from 0:00 | taken from the final timeline |
| `india-ccts-voiceover-surya-clone.mp3` / `india-ccts-final-audio-mix.mp3` | clean voice, and the full mix | |
| `thumbnail-1280x720.jpg` / `thumbnail-2560x1440.png` | YouTube thumbnail | text fits, no overlap |

## Voice (Surya's Clone Voice)
- **Engine:** offline ZipVoice, full model, 16 flow steps.
- **Speaker match:** speaker-verification score 0.918 against Surya's reference. For comparison, the reference scores 0.876 against itself, and other voices score 0.63–0.73.
- **Intelligibility:** every chunk was transcribed back with an ASR model (Parakeet TDT 0.6B), and a chunk is regenerated when its transcript drifts. All lines were reviewed. The low scores came only from acronyms ("I E E F A" scored against "IEEFA") and from digits ("CO2e", "2010"), so the read was correct in every case.
- **Name:** "Surya" is forced to the Indian pronunciation /suːɾjə/ via an IPA override. ASR confirms "I'm Surya from ReGeneva".
- **In the mix:** ASR of the final mix transcribes the narration verbatim with the music under it.

## Audio
- **Voice chain:** 75 Hz high-pass, de-esser, 2.8:1 compression, presence EQ.
- **Music:** about 16 LU below the voice, with side-chain ducking during speech.
- **Effects:** a riser and an impact on each chapter wipe.
- **Master:** −14 LUFS integrated, −1.5 dBTP limiter, no clipping.

## Visual QA
- **Coverage:** frames were checked from the rendered file in every chapter, plus the splice seams at 88.0 s, 98.0 s, 256.7 s, 286.7 s, 452.7 s and 472.7 s.
- **Defects found and fixed** in the first 4K render:
  - The glossary "GHG" molecule labels stacked vertically (a subscript layout bug).
  - The "Industrial processes 8.06%" label sat under the 47% card.
  - The status counter briefly showed "0".
- **How the fixes went in:** only the affected seconds were re-rendered. They were laid onto the original timeline by timestamp, so the frame count and audio sync stay exact.
- **Text and logos:** no text overflow in the frames checked. The logo is never distorted, and it switches between dark and light versions with the background.

## Known limitations
- **No live-action footage.** Stock-footage sites and AI video generation weren't reachable from this environment. The industrial "footage" is a procedural cinematic animation (night skyline, smoke, data grids). Licensed clips can be dropped into `scenes/index.html` later.
- **Music is synthesised, not licensed.** Tracks from the connected Epidemic Sound account couldn't be downloaded (no download permission on this account), so the score was composed and synthesised for this video and is royalty-free.
- **Government sites weren't fetched directly.** BEE, PIB, CERC and the e-Gazette sites were blocked by the network policy, so facts were verified through their published excerpts and through ICAP, IEEFA and CEEW. The ⚠ items in the evidence register should be re-checked against the gazette text before any legal use.
- **Status is a snapshot.** "First CCC issuance and trade: pending" is correct as of 31 Oct 2026. Update chapter 7 if this changes before publishing.
- **Voice source.** The clone works from a 10-second casual recording. A 30–60 s studio-quality recording would improve prosody and consistency further.

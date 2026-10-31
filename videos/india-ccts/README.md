# India's Carbon Credit Trading Scheme (CCTS): ReGeneva explainer video

A ~15-minute documentary-style explainer.
- **Narration:** in **Surya's Clone Voice**.
- **Brand:** ReGeneva colours #20C997, black and white.
- **Output:** rendered in 4K (3840×2160) and 1080p at 30 fps.
- **Research cut-off:** 31 October 2026.

## Folder structure
```
videos/india-ccts/
├── research/evidence-register.md   claims, sources, dates, status labels, exclusions
├── script/script.json              narration: "text" (captions) + "say" (voice spelling)
├── docs/creative-direction-and-storyboard.md
├── voice/
│   ├── surya-clone-voice.json      reusable voice profile (no secrets, no audio)
│   ├── zipclone.py                 ZipVoice ONNX inference (espeak IPA → flow matching → Vocos)
│   ├── build_voice.py              narration + ASR self-check + timing + SRT/chapters
│   └── preview-hook-surya-clone.mp3
├── scenes/
│   ├── index.html, style.css       every chapter as HTML/CSS
│   ├── engine.js                   deterministic timeline: setTime(t) → frame
│   ├── draw.js                     procedural canvases (skyline + smoke, data grid, charts)
│   ├── decorate.js                 chapter cards, glossary, timeline camera pan
│   └── render.js                   headless Chromium → ffmpeg (4K via scale=2)
├── audio/
│   ├── build_music.py              original synthesized score + SFX (royalty-free)
│   └── mix.sh                      voice chain, ducking, loudness (-14 LUFS), mux
├── thumbnail/                      thumbnail.html + 2560×1440 PNG + 1280×720 JPG
├── assets/                         ReGeneva logos
└── output/                         renders, narration, captions (git-ignored: too large)
```
The reusable voice skill is in `.claude/skills/surya-clone-voice/SKILL.md`.

## Rebuild
```bash
export SURYA_VOICE_MODELS=/path/to/models            # see voice/surya-clone-voice.json for downloads
export SURYA_VOICE_REF=/path/outside/repo/surya_ref24k.wav
O=videos/india-ccts/output
python3 videos/india-ccts/voice/build_voice.py $O/voice              # ~2 h on 4 CPU cores
python3 videos/india-ccts/audio/build_music.py $O/voice/timing.json $O/audio
node videos/india-ccts/scenes/render.js stills $O/voice/timing.json $O/stills 10 120 400
node videos/india-ccts/scenes/render.js video  $O/voice/timing.json $O/video_4k_silent.mp4 4 2
videos/india-ccts/audio/mix.sh $O/voice $O/audio $O/video_4k_silent.mp4 $O/india-ccts-explainer-4k.mp4
ffmpeg -i $O/india-ccts-explainer-4k.mp4 -vf scale=1920:1080:flags=lanczos -c:v libx264 -crf 18 -preset slow \
       -c:a copy -movflags +faststart $O/india-ccts-explainer-1080p.mp4
```
Tools: Python 3 (onnxruntime, sherpa-onnx, phonemizer + espeak-ng, numpy, scipy, soundfile), Node 22 + Playwright Chromium, and ffmpeg. No API keys are required.

## Editing
- **Change a line:** edit `script/script.json`, then rerun the voice, music, render and mix steps. Visual cues follow the new timing automatically.
- **Retime a visual:** change `data-c` (which narration line it belongs to) and `data-o` (seconds after that line starts) in `scenes/index.html`.
- **Update the facts:** change the status panel in chapter 7 and the dates in `research/evidence-register.md` together.

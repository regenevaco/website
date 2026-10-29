# SBTi Corporate Net-Zero Standard V2.0 — explainer video

A 9-minute, 1080p30 YouTube explainer in ReGeneva brand colours
(`#046d3a`, `#4baf47`, `#26ca86`, `#f4f3ef`; Encode Sans Condensed + Roboto).

## Deliverables
| File | What it is |
| --- | --- |
| `sbti-net-zero-v2-explainer.mp4` | Final video: H.264 1920×1080 30 fps, AAC 256 kbps, −14 LUFS |
| `thumbnail.png` | 1280×720 YouTube thumbnail |
| `captions.srt` | English subtitles (upload in YouTube Studio → Subtitles) |
| `youtube-description.md` | Title options, description with chapters, sources, tags |

## Pipeline (all local, fully reproducible)
1. `script.json`: narration. `text` is the on-screen/caption wording and `say` is the TTS-friendly spelling.
2. `build_audio.py`: synthesizes the voice-over with [Kokoro](https://github.com/thewh1teagle/kokoro-onnx)
   (voice `af_heart`) and writes `narration.wav`, `timing.json`, `captions.srt` and `chapters.txt`.
3. `build_music.py`: an original synthesized music bed and transition whooshes (royalty-free, no Content ID risk).
4. `scenes.html`: every scene as HTML/CSS. Elements animate on narration cues (`data-c` = line index,
   `data-o` = offset in seconds), driven deterministically by `window.setTime(t)`.
5. `render.js`: headless Chromium renders each frame and pipes it to ffmpeg (4 parallel workers).
6. `mix.sh`: voice processing, music ducking, loudness normalization, and the final mux.

```bash
pip install kokoro-onnx soundfile
# model files: kokoro-v1.0.onnx + voices-v1.0.bin from the kokoro-onnx GitHub release "model-files-v1.0"
python3 build_audio.py kokoro-v1.0.onnx voices-v1.0.bin build
python3 build_music.py build/timing.json build
node render.js stills build/timing.json build/stills 10 60 120   # quick previews
node render.js video  build/timing.json build/silent.mp4 4
./mix.sh build build/silent.mp4 sbti-net-zero-v2-explainer.mp4
```

To edit the narration, change `script.json` and rerun steps 2–6; the animations re-sync automatically.

## Fact base (as of October 2026)
Every claim in the video traces to SBTi's own V2.0 documents (Standard, Criteria, Executive Summary,
Main Changes Document, Scope 2 guidance, Chapter 6 on Ongoing Emissions Responsibility, press release of
11 June 2026), plus NewClimate Institute and Trellis for the reactions section. Full links are in
`youtube-description.md`. Items SBTi still lists as pending (the Claims Policy, Scope 2 exception guidance,
and the long-lived removal share for Version 3) are deliberately left out.

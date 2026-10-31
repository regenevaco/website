---
name: surya-clone-voice
description: Generate narration in "Surya's Clone Voice" (Surya's own authorised voice clone) for ReGeneva videos. Use ONLY when the user explicitly asks for Surya's voice / Surya's Clone Voice for a narration or voiceover.
---

# Surya's Clone Voice

An offline, zero-shot clone of Surya's Indian-English voice, authorised by Surya for ReGeneva narration only.
- **Engine:** ZipVoice (k2-fsa, Apache-2.0) run through ONNX Runtime, with a Vocos 24 kHz vocoder.
- **Cost and access:** no cloud provider, no API key.
- **Profile:** `videos/india-ccts/voice/surya-clone-voice.json`. The engine is `videos/india-ccts/voice/zipclone.py`.

## Rules
- Use the voice only for Surya / ReGeneva content that the user asked to be narrated in Surya's voice. Never use it for any other person, and never make it say things Surya wouldn't sign off on.
- The reference recording is personal data. Keep it **outside the repository**, point `SURYA_VOICE_REF` at it, and never commit, upload or share it.
- Don't claim a narration was produced in this voice unless the build actually ran and passed its ASR check.

## Setup (once per machine/session)
1. Create a model folder and set `SURYA_VOICE_MODELS` to it.
2. Download the files listed under `model.download` in the profile JSON from the GitHub releases and extract them:
   - `sherpa-onnx-zipvoice-zh-en-emilia`
   - `sherpa-onnx-zipvoice-distill-int8-zh-en-emilia` (needed only for `tokens.txt`)
   - `vocos_24khz.onnx`
   - `sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` (the ASR check)
3. Install the Python packages: `pip install onnxruntime sherpa-onnx espeakng-loader phonemizer soundfile scipy`.
4. Convert Surya's reference to 24 kHz mono WAV and point `SURYA_VOICE_REF` at it:
   `ffmpeg -i Surya-voice-clone.mp3 -ar 24000 -ac 1 surya_ref24k.wav`
   The transcript in the profile must match the recording exactly. If Surya supplies a new or longer reference (30–60 s of clean, studio-quality speech improves quality), update `reference_transcript`.

## Writing narration for this voice
- Write a `script.json` with both `text` (captions) and `say` (what the voice reads). Follow `pronunciation_tips` in the profile:
  - Spell acronyms with spaces: "C C T S".
  - Write years as words.
  - Write "C O two e" for CO₂e.
- Keep sentences 8–35 words long. The builder groups shorter sentences together automatically.

## Generate
```bash
cd videos/<project>/voice    # or copy build_voice.py next to your script
python3 build_voice.py <out_dir> --only <scene_id>   # quick preview of one scene
python3 build_voice.py <out_dir>                     # full narration
```
Outputs:
- `narration.wav`: the full narration
- `lines/*.wav`: one file per line
- `timing.json`: for syncing visuals
- `captions.srt`, `chapters.txt`
- `voice_qa.json`: the ASR transcript and similarity for every chunk. Chunks below 0.8 are retried with new seeds, up to 4 times.

On a 4-core CPU, generation runs at roughly 6–10× real time.

## QA before delivering
- Read `voice_qa.json`. Any chunk with `similarity < 0.9` needs a listen, or a rewrite of its `say` text.
- Speaker similarity at setup was 0.918 (WeSpeaker) against a self-similarity of 0.876, so the clone matches the reference about as well as the reference matches itself.

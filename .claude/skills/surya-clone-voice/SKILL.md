---
name: surya-clone-voice
description: Generate ReGeneva narration in Surya's own authorised cloned voice. Two profiles: "Surya Indian Accent Original Voice Clone" (India-focused content) and "Surya US Accent Clone" (global content). Use ONLY when the user asks for Surya's voice for a voiceover.
---

# Surya's voice clones

| Profile | File | Use for |
|---|---|---|
| **Surya Indian Accent Original Voice Clone** | `videos/india-ccts/voice/profiles/surya-indian-accent-original-voice-clone.json` | India-focused topics and Indian audiences (CCTS, BRSR, Indian regulation) |
| **Surya US Accent Clone** | `videos/india-ccts/voice/profiles/surya-us-accent-clone.json` | Global topics and international audiences |

## Rules
- Use these voices only for ReGeneva content that the user asked to have narrated in Surya's voice. Never use them for another person, and never make them say anything Surya wouldn't sign off on.
- Surya's recordings are personal data. Keep them outside the repository (`SURYA_VOICE_REF_DIR`, `SURYA_MATCH_WAV`) and never commit, upload or share them.
- Never say Surya's name in a video unless the user asks for it. Disclose that the narration is AI-generated (end-card fine print, plus YouTube's "Altered or synthetic content" setting).
- Don't claim audio was produced in a voice unless the build ran and passed its ASR check.

## Indian accent profile (ZipVoice, offline)
- **Source:** four style reference clips cut from Surya's 11.8-minute sample, each with an exact transcript.
- **Picking a style per line:** set `"style"` on each line of `script.json`:
  - `curious`: hooks, questions, high energy
  - `emphatic`: thought-provoking points, key takeaways
  - `explanatory`: teaching and data
  - `warm`: closings and calls to action
- **Speed per style:** `style_speed` in the profile.
- **Setup:**
  1. Download the files listed under `model.download` into `SURYA_VOICE_MODELS`.
  2. `pip install onnxruntime sherpa-onnx espeakng-loader phonemizer soundfile scipy`
  3. Put the style clips in `SURYA_VOICE_REF_DIR`. To recreate them from the original sample: polish with `highpass=f=70,afftdn=nr=10:nf=-50,loudnorm=I=-18:TP=-2`, resample to 24 kHz mono, then cut at the timestamps listed in the profile's `styles`.
- **Generate:**
  - `python3 videos/india-ccts/voice/build_voice.py <out_dir> --only <scene>` renders one scene.
  - Then `--assemble` produces `narration.wav`, `timing.json`, `captions.srt` and `chapters.txt`.
  - Each chunk is transcribed by ASR and regenerated when it drifts from the script (`voice_qa.json`).
- **Pronunciation:**
  - Spell acronyms with spaces ("C C T S", "I E E F A").
  - "C O two e" for CO₂e, and "see bam" for CBAM.
  - Write years as words.
  - Use `[[IPA]]` for names, e.g. `[[sˈuːɹjə]]`.

## US accent profile (Kokoro → kNN-VC)
- **Pipeline:** a US-English Kokoro voice gives the accent and rhythm. kNN-VC (WavLM-Large + pre-matched HiFi-GAN, MIT licence) then converts the timbre to Surya's, using his long recording as the matching set.
- **Status:** the code is in `videos/india-ccts/voice/usclone.py`. Running the third-party kNN-VC code needs the user's explicit permission in this environment. Validate it (ASR plus speaker similarity) before first use, and record the scores in the profile.

## QA before delivery
- Read `voice_qa.json`. Any chunk with `similarity < 0.85` needs listening to, or its `say` text rewritten (scores dip on spelled acronyms and digits).
- Speaker similarity (WeSpeaker) of the Indian profile against Surya's recording is 0.92–0.95. His own recording scores 0.959 against itself.

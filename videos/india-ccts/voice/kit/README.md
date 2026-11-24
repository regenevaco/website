# Surya Voice Clone kit (Indian-accent original)

AI voice clone of Surya Narayan Kar (ReGeneva), made from his own 11.8-minute recording with his consent.
**Private: this folder contains Surya's voice recordings. Don't share it publicly or use it for anyone else's content.**
Any video using this voice must be marked as AI-generated (on YouTube: "Altered or synthetic content" → Yes).

## What's inside
| File | Purpose |
|---|---|
| `refs/*.wav` | Four short reference clips of Surya, one per delivery style |
| `profiles/surya-indian-accent-original-voice-clone.json` | Voice profile (styles, speeds, settings, validation scores) |
| `speak.sh` | One command: text in → WAV + MP3 out |
| `say_line.py`, `build_voice.py`, `zipclone.py` | Generation engine (ZipVoice zero-shot TTS) with automatic quality checks |
| `setup.sh` | One-time install: Python packages + open-source models (~1.5 GB, downloaded from GitHub) |
| `usclone.py`, `profiles/surya-us-accent-clone.json` | Indo-US accent pipeline: **not built yet** (see below) |
| `demo.mp3` | Sample output |

## Setup (once)
Needs Linux or macOS, Python 3.10+, ffmpeg and internet access to github.com.
```bash
./setup.sh
```

## Use
```bash
./speak.sh "Book a free consult now for your team." cta              # best of warm + emphatic
./speak.sh "Here is how the scheme works." line1 explanatory          # one style
SAY="Book a free consult now, for your team, by scanning this Q R code." \
  ./speak.sh "Book a free consult now for your team by scanning this QR code." cta2
```
Each run makes 4 takes per style, transcribes each one to check the words, and scores how closely it matches Surya's voice. It keeps the best take, then cleans, EQs and compresses it. Output:
- `NAME.wav` (48 kHz, 24-bit, −16 LUFS)
- `NAME.mp3` (320 kbps)
- `NAME.json` (scores for every take)

## Styles
- **explanatory**: clearest and most neutral; best for teaching and for international audiences
- **warm**: friendly; best for closings and calls to action
- **emphatic**: confident; best for key points
- **curious**: high energy; best for hooks and questions

## Pronunciation tips
- Spell acronyms with spaces: "C C T S", "Q R", "E S G".
- Write numbers and years as words: "twenty twenty-six".
- Put commas where Surya would pause.
- Pass the spoken version in `SAY="..."` and the display text as the first argument.
- For a name the engine gets wrong, write its IPA in double brackets, e.g. `[[sˈuːɹjə]]`.

## Quality
Speaker similarity to Surya's own recording is typically 0.89–0.95. His recording scores 0.959 against itself.

## Indo-US accent version (pending)
`usclone.py` would make a US-English voice speak the text, then rebuild it from Surya's own recorded sounds (kNN-VC), giving an Indo-US blend.
Running that third-party conversion code was blocked by the safety settings of the environment where this kit was made.
It needs explicit permission to run, plus its model weights (WavLM-Large, kNN-VC HiFi-GAN and Kokoro).

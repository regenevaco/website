"""One-off line in Surya's cloned voice (Indian accent profile), with automatic take selection.

    python3 say_line.py "<text to show>" "<text to say>" <out_basename> [style ...]

Generates several takes per style (warm / emphatic / curious / explanatory), scores each one by
  - ASR word accuracy against the text (Parakeet), and
  - speaker similarity to Surya's reference clips (WeSpeaker),
keeps the best, polishes it (rumble cut, presence EQ, gentle compression, -16 LUFS / -1.5 dBTP)
and writes <out>.wav (48 kHz / 24-bit) and <out>.mp3 (320 kbps), plus <out>.json with the scores.
Environment: SURYA_VOICE_MODELS, SURYA_VOICE_REF_DIR (see the surya-clone-voice skill).
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_voice import PROFILE, SR, load_voice, similarity, trim  # noqa: E402

TAKES = 4


def speaker_model(models):
    import sherpa_onnx
    return sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=os.path.join(models, "wespeaker_en_voxceleb_resnet34_LM.onnx")))


def embed(ex, wav, sr):
    with tempfile.NamedTemporaryFile(suffix=".wav") as a, tempfile.NamedTemporaryFile(suffix=".wav") as b:
        sf.write(a.name, wav, sr)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.name, "-ar", "16000", "-ac", "1", b.name], check=True)
        x, r = sf.read(b.name, dtype="float32")
    st = ex.create_stream()
    st.accept_waveform(r, x)
    st.input_finished()
    e = np.array(ex.compute(st))
    return e / np.linalg.norm(e)


def main(show, say, out, *styles):
    styles = styles or ("warm", "emphatic")
    models, refs = os.environ["SURYA_VOICE_MODELS"], os.environ["SURYA_VOICE_REF_DIR"]
    voice, checker = load_voice()
    ex = speaker_model(models)
    ref = np.mean([embed(ex, *sf.read(os.path.join(refs, s["file"]), dtype="float32"))
                   for s in PROFILE["styles"].values()], axis=0)
    ref /= np.linalg.norm(ref)
    g = PROFILE["generation"]
    takes = []
    for style in styles:
        for k in range(TAKES):
            w = trim(voice.say(say, speed=PROFILE["style_speed"].get(style, 1.0), prompt=style, steps=g["steps"],
                               guidance=g["guidance"], t_shift=g["t_shift"], seed=7000 + 13 * k + len(style)))
            heard = checker.transcribe(w)
            acc = similarity(show, heard)
            spk = float(embed(ex, w, SR) @ ref)
            takes.append({"style": style, "take": k, "asr": round(acc, 3), "speaker": round(spk, 3), "heard": heard,
                          "score": round(acc + spk, 3), "wav": w})
            print(f"{style} #{k}: asr={acc:.2f} speaker={spk:.3f} | {heard}", flush=True)
    best = max(takes, key=lambda t: (t["asr"] >= 0.95, t["score"]))
    raw = f"{out}_raw.wav"
    sf.write(raw, np.concatenate([np.zeros(int(0.25 * SR), np.float32), best["wav"], np.zeros(int(0.35 * SR), np.float32)]), SR)
    chain = ("highpass=f=75,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3300:t=q:w=1.3:g=2.2,"
             "equalizer=f=9500:t=q:w=0.9:g=1.2,deesser=i=0.3,"
             "acompressor=threshold=-22dB:ratio=2.5:attack=6:release=120:makeup=2,"
             "loudnorm=I=-16:TP=-1.5:LRA=7,pan=stereo|c0=c0|c1=c0")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", chain, "-ar", "48000",
                    "-c:a", "pcm_s24le", f"{out}.wav"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{out}.wav", "-c:a", "libmp3lame", "-b:a", "320k",
                    f"{out}.mp3"], check=True)
    os.remove(raw)
    json.dump({"text": show, "said": say, "chosen": {k: v for k, v in best.items() if k != "wav"},
               "takes": [{k: v for k, v in t.items() if k != "wav"} for t in takes]},
              open(f"{out}.json", "w"), indent=2)
    print("chosen:", best["style"], best["take"], "asr", best["asr"], "speaker", best["speaker"])


if __name__ == "__main__":
    main(*sys.argv[1:])

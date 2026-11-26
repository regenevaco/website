"""Stage 3: edited + polished opener audio.

    python3 audio.py <work_dir> <speed>

Reads work_dir/a48.wav and work_dir/edl.json and writes:
  voice_edit.wav    the kept segments joined (5 ms fades at each join, no overlap, so sync is exact)
  voice_polish.wav  cleaned, EQ'd, compressed, sped up (pitch kept), stereo
  music_bed/        a royalty-free bed from ../audio/build_music.py, scored to the opener length
  opener_mix.wav    voice + ducked music, -14 LUFS / -1.5 dBTP (matches the explainer mix)
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))


def main(work, speed):
    speed = float(speed)
    x, sr = sf.read(f"{work}/a48.wav", dtype="float32")
    x = x.mean(1) if x.ndim > 1 else x
    edl = json.load(open(f"{work}/edl.json"))
    spf = sr // edl["fps"]                     # samples per video frame (1600)
    f = int(0.005 * sr)
    parts = []
    for a, b, _ in edl["segments"]:
        seg = x[a * spf:b * spf].copy()
        seg[:f] *= np.linspace(0, 1, f)
        seg[-f:] *= np.linspace(1, 0, f)
        parts.append(seg)
    v = np.concatenate(parts)
    sf.write(f"{work}/voice_edit.wav", v, sr, subtype="PCM_24")

    # Voice polish: rumble cut, light denoise, de-mud, presence and air, de-ess, two-stage compression,
    # tempo up (pitch preserved), centred stereo.
    chain = (f"highpass=f=80,afftdn=nr=10:nf=-55,"
             f"equalizer=f=250:t=q:w=1.2:g=-2.5,equalizer=f=3400:t=q:w=1.3:g=2.8,"
             f"equalizer=f=9500:t=q:w=0.9:g=1.6,deesser=i=0.4,"
             f"acompressor=threshold=-24dB:ratio=3:attack=5:release=120:makeup=2,"
             f"acompressor=threshold=-14dB:ratio=6:attack=1:release=60,"
             f"atempo={speed},pan=stereo|c0=c0|c1=c0")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/voice_edit.wav", "-af", chain,
                    "-ar", "48000", "-c:a", "pcm_s24le", f"{work}/voice_polish.wav"], check=True)
    dur = sf.info(f"{work}/voice_polish.wav").duration

    # Music bed: same synthesized palette as the explainer (optimistic "light" cue), scored to this length.
    os.makedirs(f"{work}/music_bed", exist_ok=True)
    timing = {"total": dur, "scenes": [{"id": "opener", "tone": "light", "start": 0, "dur": dur,
                                        "lines": [{"start": 0}]}]}
    json.dump(timing, open(f"{work}/music_bed/timing.json", "w"))
    subprocess.run(["python3", os.path.join(HERE, "..", "audio", "build_music.py"),
                    f"{work}/music_bed/timing.json", f"{work}/music_bed"], check=True)

    # Mix: music ducked under the voice (sidechain), then loudness-normalised like the explainer.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/voice_polish.wav",
                    "-i", f"{work}/music_bed/music.wav", "-filter_complex",
                    "[0:a]asplit=2[v][k];[1:a]volume=0.16[m];"
                    "[m][k]sidechaincompress=threshold=0.05:ratio=3:attack=60:release=700[d];"
                    "[v][d]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[o]",
                    "-map", "[o]", "-ar", "48000", "-c:a", "pcm_s24le", f"{work}/opener_mix.wav"], check=True)
    print(f"edited {len(v) / sr:.2f}s -> {dur:.2f}s at x{speed}")


if __name__ == "__main__":
    main(*sys.argv[1:3])

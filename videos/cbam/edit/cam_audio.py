"""Edited + polished audio for one on-camera clip (pauses trimmed per the cut list, no speed change).

    python3 cam_audio.py <clip_48k.wav> <edl.json> <out.wav>

Kept segments are joined with 5 ms fades (sample-exact to the video frames), then polished:
rumble cut, light denoise, de-mud, presence and air, de-ess, gentle two-stage compression, centred stereo.
Loudness is set later, in the final mix, together with the narration (-14 LUFS overall).
"""
import json
import subprocess
import sys

import numpy as np
import soundfile as sf


def main(wav, edl_json, out):
    x, sr = sf.read(wav, dtype="float32")
    x = x.mean(1) if x.ndim > 1 else x
    edl = json.load(open(edl_json))
    spf = sr // edl["fps"]
    f = int(0.005 * sr)
    parts = []
    for a, b, _ in edl["segments"]:
        seg = x[a * spf:b * spf].copy()
        if len(seg) < (b - a) * spf:                       # clip audio slightly shorter than video
            seg = np.pad(seg, (0, (b - a) * spf - len(seg)))
        seg[:f] *= np.linspace(0, 1, f)
        seg[-f:] *= np.linspace(1, 0, f)
        parts.append(seg)
    tmp = out.replace(".wav", "_raw.wav")
    sf.write(tmp, np.concatenate(parts), sr, subtype="PCM_24")
    chain = ("highpass=f=80,afftdn=nr=10:nf=-55,"
             "equalizer=f=250:t=q:w=1.2:g=-2.5,equalizer=f=3400:t=q:w=1.3:g=2.8,"
             "equalizer=f=9500:t=q:w=0.9:g=1.6,deesser=i=0.4,"
             "acompressor=threshold=-24dB:ratio=3:attack=5:release=120:makeup=2,"
             "acompressor=threshold=-14dB:ratio=6:attack=1:release=60,"
             "pan=stereo|c0=c0|c1=c0")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-af", chain, "-ar", "48000",
                    "-c:a", "pcm_s24le", out], check=True)
    print(out, round(sum(b - a for a, b, _ in edl["segments"]) / edl["fps"], 2), "s")


if __name__ == "__main__":
    main(*sys.argv[1:4])

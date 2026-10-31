"""Original, royalty-free score + sound design, scored to the narration timeline.

    python3 build_music.py <timing.json> <out_dir>

Writes music.wav (48 kHz stereo) and sfx.wav. Every sound is synthesized here,
so there is nothing to license and nothing for YouTube Content ID to claim.

Cue sheet (driven by each scene's "tone" and position):
  hook          dark tension: sub drone, heartbeat pulse, shimmer; impact at the title
  light scenes  optimistic corporate pulse: F-C-Dm-Bb, plucked 8ths, warm pad
  dark scenes   investigative: Dm-Bb-F-C, sparse bell motif, ticking 16ths
  close         inspirational lift: full pad, bell melody, rising strings, final chord
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(7)

LIGHT = [[53, 57, 60, 64], [48, 55, 60, 64], [50, 57, 60, 65], [46, 53, 58, 62]]   # Fmaj7 C Dm Bb
DARK = [[50, 57, 62, 65], [46, 53, 58, 62], [41, 53, 57, 60], [48, 55, 60, 64]]    # Dm Bb F C
CLOSE = [[46, 53, 58, 62, 65], [41, 53, 57, 60, 65], [48, 55, 60, 64, 67], [50, 57, 62, 65, 69]]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=0)


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na) if na else 1
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def saw_pad(freq, n, detune=0.08):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in (-detune, 0, detune):
        f = freq * 2 ** (d / 12)
        for k in range(1, 9):
            out += np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6.28)) / k
    return out / 3


def fm_pluck(freq, dur, ratio=2.0, index=2.5, decay=6.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * ratio * t) * index * np.exp(-t * decay * 1.5)
    return np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * decay) * np.minimum(1, t / 0.003)


def bell(freq, dur):
    return 0.7 * fm_pluck(freq, dur, ratio=3.5, index=1.8, decay=2.2) + 0.3 * fm_pluck(freq * 2, dur, 1.0, 0.5, 3.5)


def place(buf, sig, at, gain=1.0, pan=0.5):
    a = int(at * SR)
    if a >= len(buf) or a < 0:
        return
    b = min(len(buf), a + len(sig))
    buf[a:b, 0] += sig[: b - a] * gain * np.sqrt(1 - pan)
    buf[a:b, 1] += sig[: b - a] * gain * np.sqrt(pan)


def section(kind, dur, seed):
    """Render one cue of length dur seconds (stereo)."""
    n = int((dur + 3) * SR)
    out = np.zeros((n, 2))
    prog = {"light": LIGHT, "dark": DARK, "close": CLOSE, "hook": DARK}[kind]
    chord_len = 2 * BAR
    t = 0.0
    k = 0
    while t < dur + 1:
        notes = prog[k % len(prog)]
        cn = int((chord_len + 1.5) * SR)
        pad = sum(saw_pad(hz(m), cn) for m in notes[1:]) * env_adsr(cn, 1.2, 1.5)
        pad = lp(pad, 900 if kind != "close" else 1600 + 400 * min(1, t / dur * 2))
        place(out, pad, t, 0.05 if kind != "hook" else 0.035, 0.42)
        place(out, pad, t + 0.013, 0.05 if kind != "hook" else 0.035, 0.58)
        # bass
        bass = np.sin(2 * np.pi * hz(notes[0] - 12) * np.arange(cn) / SR) * env_adsr(cn, 0.4, 1.0)
        place(out, bass, t, 0.16 if kind != "hook" else 0.2, 0.5)
        steps = int(chord_len / (BEAT / 2))
        for s in range(steps):
            at = t + s * BEAT / 2
            if kind == "light":
                m = notes[[1, 2, 3, 2, 1, 3, 2, 3][s % 8]] + 12
                place(out, fm_pluck(hz(m), 0.6), at, 0.11 if s % 2 == 0 else 0.07, 0.3 + 0.4 * ((s * 3) % 4) / 3)
            elif kind in ("dark", "hook"):
                tick = hp(rng.standard_normal(int(0.03 * SR)) * np.exp(-np.arange(int(0.03 * SR)) / SR * 160), 6000)
                place(out, tick, at, 0.05 if s % 2 else 0.03, 0.5 + 0.3 * np.sin(s))
                place(out, tick, at + BEAT / 4, 0.02, 0.4)
                if kind == "dark" and s % 8 == 0:
                    place(out, bell(hz(notes[[3, 2, 3, 1][(s // 8 + k) % 4]] + 12), 3.0), at, 0.09, 0.6)
            elif kind == "close":
                m = notes[[1, 2, 3, 4, 3, 2][s % 6]] + 12
                place(out, fm_pluck(hz(m), 0.7), at, 0.09, 0.3 + 0.4 * (s % 3) / 2)
                if s % 4 == 0:
                    place(out, bell(hz(notes[-1] + 12), 3.0), at, 0.07, 0.5)
        if kind == "hook":
            for b in range(int(chord_len / BEAT)):
                at = t + b * BEAT
                thump = np.sin(2 * np.pi * 52 * np.arange(int(0.35 * SR)) / SR) * np.exp(-np.arange(int(0.35 * SR)) / SR * 12)
                place(out, thump, at, 0.32 if b % 2 == 0 else 0.18, 0.5)
        t += chord_len
        k += 1
    if kind in ("dark", "hook"):
        drone = saw_pad(hz(38), n, 0.05)
        drone = lp(drone, 260) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.05 * np.arange(n) / SR))
        place(out, drone, 0, 0.05, 0.5)
    return out[: int(dur * SR)]


def reverb(x, secs=2.6, wet=0.28):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)], 1) * np.exp(-t * 3.2)[:, None]
    ir = lp(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum(0))
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet) + y * wet * 2.2


def noise_sweep(dur, up=True):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    e = np.linspace(0, 1, n) ** 2 if up else np.linspace(1, 0, n) ** 2
    lo, hi = lp(noise, 1200), lp(noise, 7000)
    s = np.linspace(0, 1, n) if up else np.linspace(1, 0, n)
    return (lo * (1 - s) + (hi - lo) * s) * e


def impact():
    n = int(2.4 * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (60 * np.exp(-t * 3) + 32) * t) * np.exp(-t * 2.2)
    air = lp(rng.standard_normal(n), 3000) * np.exp(-t * 4) * 0.25
    return boom + air


def main():
    timing = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    total = timing["total"] + 1.0
    n = int(total * SR)
    music = np.zeros((n, 2))
    scenes = timing["scenes"]
    xf = 1.6
    for i, sc in enumerate(scenes):
        kind = "hook" if sc["id"] == "hook" else ("close" if sc["id"] == "close" else sc["tone"])
        start = max(0, sc["start"] - xf / 2)
        end = min(total, sc["start"] + sc["dur"] + xf / 2)
        seg = section(kind, end - start, i)
        m = len(seg)
        fade = np.ones(m)
        f = int(xf * SR)
        if i > 0:
            fade[:f] = np.linspace(0, 1, f)
        if i < len(scenes) - 1:
            fade[-f:] *= np.linspace(1, 0, f)
        a = int(start * SR)
        music[a: a + m] += seg * fade[:, None]
    # hook: hold music back during the title reveal, then hit
    music = reverb(music)
    fade_in, fade_out = int(1.5 * SR), int(5 * SR)
    music[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    music[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    music /= np.max(np.abs(music)) + 1e-9
    sf.write(os.path.join(out, "music.wav"), (music * 0.85).astype(np.float32), SR)

    sfx = np.zeros((n, 2))
    sweep = noise_sweep(1.2)
    hit = impact()
    for i, sc in enumerate(scenes):
        if i == 0:
            continue
        place(sfx, sweep, sc["start"] - 0.9, 0.22, 0.4)
        place(sfx, sweep, sc["start"] - 0.88, 0.22, 0.6)
        place(sfx, hit, sc["start"] + 0.25, 0.5, 0.5)
    hook = scenes[0]
    title_at = hook["start"] + hook["lines"][-1]["start"]
    place(sfx, noise_sweep(2.5), title_at - 2.3, 0.3, 0.5)
    place(sfx, hit, title_at + 0.2, 0.9, 0.5)
    sfx = reverb(sfx, 1.8, 0.3)
    sfx /= np.max(np.abs(sfx)) + 1e-9
    sf.write(os.path.join(out, "sfx.wav"), (sfx * 0.9).astype(np.float32), SR)
    print("music", total, "s")


if __name__ == "__main__":
    main()

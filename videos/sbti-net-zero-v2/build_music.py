"""Generate an original, royalty-free music bed and transition whooshes.

Usage: python3 build_music.py <timing.json> <out_dir>
Writes music.wav (stereo, 48 kHz) and sfx.wav (transition whooshes).
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

SR = 48000
BPM = 96
BEAT = 60 / BPM
# Bright, optimistic progression: Cmaj9 - Am7 - Fmaj7 - Gsus2/G (two bars each)
CHORDS = [
    [48, 55, 59, 62, 64],
    [45, 52, 55, 60, 64],
    [41, 48, 52, 57, 60],
    [43, 50, 55, 57, 62],
]
BARS_PER_CHORD = 2


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, cutoff):
    # one-pole low-pass, applied twice for a gentler slope
    a = np.exp(-2 * np.pi * cutoff / SR)
    for _ in range(2):
        y = np.empty_like(x)
        acc = 0.0
        for i in range(0, len(x), 4096):
            seg = x[i:i + 4096]
            out = np.empty_like(seg)
            for j, v in enumerate(seg):
                acc = (1 - a) * v + a * acc
                out[j] = acc
            y[i:i + 4096] = out
        x = y
    return x


def pad(total):
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2), dtype=np.float64)
    chord_len = BARS_PER_CHORD * 4 * BEAT
    k = 0
    start = 0.0
    while start < total:
        notes = CHORDS[k % len(CHORDS)]
        a, b = int(start * SR), min(n, int((start + chord_len + 2.0) * SR))
        tt = t[a:b] - start
        env = np.minimum(1, tt / 1.6) * np.clip((chord_len + 2.0 - tt) / 2.0, 0, 1)
        for m in notes:
            f = hz(m + 12)
            for det, pan in ((-0.12, 0.3), (0.12, 0.7)):
                ff = f * 2 ** (det / 12)
                w = np.sin(2 * np.pi * ff * tt) + 0.25 * np.sin(4 * np.pi * ff * tt) + 0.08 * np.sin(6 * np.pi * ff * tt)
                out[a:b, 0] += w * env * (1 - pan) * 0.05
                out[a:b, 1] += w * env * pan * 0.05
        # soft bass on the root
        root = hz(notes[0] - 12)
        out[a:b, :] += (np.sin(2 * np.pi * root * tt) * env * 0.09)[:, None]
        start += chord_len
        k += 1
    return out


def arp(total):
    n = int(total * SR)
    out = np.zeros((n, 2))
    step = BEAT / 2
    pattern = [0, 2, 4, 3, 1, 4, 2, 3]
    chord_len = BARS_PER_CHORD * 4 * BEAT
    i = 0
    t0 = 0.0
    while t0 < total:
        notes = CHORDS[int(t0 // chord_len) % len(CHORDS)]
        m = notes[pattern[i % len(pattern)]] + 24
        f = hz(m)
        L = int(1.2 * SR)
        a = int(t0 * SR)
        b = min(n, a + L)
        tt = np.arange(b - a) / SR
        env = np.exp(-tt * 5.5) * np.minimum(1, tt / 0.004)
        w = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * env
        vel = 0.030 if i % 2 == 0 else 0.020
        pan = 0.35 + 0.3 * ((i * 3) % 4) / 3
        out[a:b, 0] += w * vel * (1 - pan)
        out[a:b, 1] += w * vel * pan
        i += 1
        t0 += step
    return out


def echo(x, delay=BEAT * 0.75, fb=0.32, mix=0.35):
    d = int(delay * SR)
    y = x.copy()
    for k in range(1, 5):
        g = mix * fb ** (k - 1)
        y[d * k:, 0] += x[:-d * k, 1] * g  # ping-pong
        y[d * k:, 1] += x[:-d * k, 0] * g
    return y


def whoosh(dur=0.9, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    # sweep a resonant band-pass by mixing two low-pass outputs
    lo = lowpass(noise, 900)
    hi = lowpass(noise, 4000)
    sweep = np.clip(t / dur, 0, 1)
    w = (lo * (1 - sweep) + (hi - lo) * sweep) * env
    w /= np.max(np.abs(w)) + 1e-9
    return np.stack([w * 0.9, w], axis=1)


def main():
    timing = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    total = timing["total"] + 0.5
    music = pad(total) + echo(arp(total))
    # gentle fades
    n = len(music)
    fade = np.ones(n)
    fi, fo = int(2.0 * SR), int(5.0 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    music *= fade[:, None]
    music /= np.max(np.abs(music)) + 1e-9
    sf.write(os.path.join(out, "music.wav"), (music * 0.8).astype(np.float32), SR)

    sfx = np.zeros((n, 2))
    w = whoosh()
    for i, s in enumerate(timing["scenes"][1:]):
        a = int(max(0, s["start"] - 0.35) * SR)
        b = min(n, a + len(w))
        sfx[a:b] += w[: b - a] * (0.5 if i % 2 else 0.42)
    sf.write(os.path.join(out, "sfx.wav"), sfx.astype(np.float32), SR)
    print("music", n / SR, "s")


if __name__ == "__main__":
    main()

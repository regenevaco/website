"""Synthesized sound effects (nothing to license): button click, bell ding, soft whoosh.

    python3 sfx.py <out_dir>
"""
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000


def click():
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    x = np.random.default_rng(1).standard_normal(n) * np.exp(-t * 180)
    x = sosfilt(butter(2, [1800, 7000], "band", fs=SR, output="sos"), x)
    x += 0.5 * np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120)
    return x / np.abs(x).max() * 0.5


def ding():
    d = 1.8
    t = np.arange(int(d * SR)) / SR
    f0 = 1318.5                                   # E6, a bright notification bell
    x = np.zeros_like(t)
    for ratio, amp, dec in [(1, 1.0, 2.4), (2.0, 0.35, 3.5), (2.76, 0.22, 4.5), (5.4, 0.08, 7)]:
        x += amp * np.sin(2 * np.pi * f0 * ratio * t) * np.exp(-t * dec)
    x *= np.clip(t / 0.003, 0, 1)
    return x / np.abs(x).max() * 0.6


def whoosh():
    d = 0.9
    n = int(SR * d)
    t = np.arange(n) / SR
    x = np.random.default_rng(3).standard_normal(n)
    out = np.zeros(n)
    for i in range(0, n, 480):
        f = 400 * (5000 / 400) ** (i / n)
        sos = butter(2, [f * 0.7, min(f * 1.4, 23000)], "band", fs=SR, output="sos")
        out[i:i + 480] = sosfilt(sos, x[max(0, i - 2000):i + 480])[-len(out[i:i + 480]):]
    y = out * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return y / (np.abs(y).max() + 1e-9) * 0.5


if __name__ == "__main__":
    out = sys.argv[1]
    for name, fn in (("click", click), ("ding", ding), ("whoosh", whoosh)):
        y = fn().astype(np.float32)
        sf.write(f"{out}/{name}.wav", np.stack([y, y], 1), SR)
        print(name, round(len(y) / SR, 2), "s")

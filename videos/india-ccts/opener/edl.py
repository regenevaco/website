"""Stage 2: edit decision list for the to-camera opener.

    python3 edl.py <work_dir>

Inputs in work_dir: a48.wav (camera audio), words.json ([word, start_s] from ASR).
Output: work_dir/edl.json -> {"fps": 30, "segments": [[src_frame_in, src_frame_out, kind], ...]}
kind = "sentence" (cut after a sentence end: zoom change allowed) or "micro" (a trimmed pause).

Rules
- Remove the false starts / doubles listed in CUTS (word ranges, by index).
- Shorten every silence longer than MAX_GAP; keep a natural tail after each phrase.
- Cut points sit in the quietest 10 ms frame between words and are snapped to video frames.
"""
import json
import sys

import numpy as np
import soundfile as sf

FPS = 30
MAX_GAP = 0.30          # silences longer than this are shortened
KEEP_SENT = 0.34        # pause kept after a sentence (s)
KEEP_MICRO = 0.16       # pause kept inside a sentence (s)


def main(work):
    x, sr = sf.read(f"{work}/a48.wav", dtype="float32")
    x = x.mean(1) if x.ndim > 1 else x
    hop = sr // 100
    db = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, "same")[::hop]) + 1e-9)
    words = json.load(open(f"{work}/words.json"))
    T = len(x) / sr
    starts = [s for _, s in words]
    names = [w for w, _ in words]

    # Pauses are found with a strict mask (room floor + 20 dB, so breaths and clicks count as silence);
    # each kept edge is then extended through the soft onset / decay of the neighbouring word
    # (anything above floor + 9 dB that touches the word), so quiet sounds like "r", "h", "w" survive.
    floor = np.percentile(db, 10)
    sp = db > floor + 20
    k = 6
    sp = np.convolve(sp.astype(float), np.ones(2 * k + 1), "same") > 0
    soft = db > floor + 9

    def quietest(a, b):
        i0, i1 = int(a * 100), max(int(a * 100) + 1, int(b * 100))
        return (i0 + int(np.argmin(db[i0:i1]))) / 100

    def find(word, near):
        idx = [i for i, w in enumerate(names) if w.lower().strip(".,?!") == word]
        return min(idx, key=lambda i: abs(starts[i] - near))

    # Content cuts: (first word removed, first word kept after), located by word + approximate time.
    cuts = []
    for w0, t0, w1, t1 in [("by", 62.5, "every", 65.8),       # "By the end of the year," (said again 9 s later)
                           ("is", 87.1, "is", 87.4),           # "is is" -> "is"
                           ("with", 118.8, "with", 119.3)]:    # "let's begin with. With the example" -> "with the example"
        i, j = find(w0, t0), find(w1, t1)
        a = quietest(starts[i] - 0.25, starts[i] + 0.05)
        b = quietest(starts[j] - 0.25, starts[j] + 0.02)
        cuts.append((a, b))

    # Region to use: from just before the first word to the end of the last word.
    first = starts[0] - 0.12
    last_on = np.where(sp[int(starts[-1] * 100):])[0]
    end = starts[-1] + (last_on[-1] / 100 if len(last_on) else 0.6) + 0.25

    keep = np.zeros(int(T * 100) + 1, bool)
    keep[int(first * 100):int(end * 100)] = True
    for a, b in cuts:
        keep[int(a * 100):int(b * 100)] = False

    # Shorten silences inside kept regions.
    sent_end = {round(s, 2) for w, s in words if w.endswith((".", "?", "!"))}
    i = int(first * 100)
    while i < int(end * 100):
        if keep[i] and not sp[i]:
            j = i
            while j < len(sp) and keep[j] and not sp[j]:
                j += 1
            gap = (j - i) / 100
            prev_words = [s for s in starts if s * 100 < i]
            is_sent = bool(prev_words) and round(prev_words[-1], 2) in sent_end
            want = KEEP_SENT if is_sent else KEEP_MICRO
            if gap > MAX_GAP and gap > want:
                on = j                                      # walk back through the soft onset
                while on > i and soft[on - 1]:
                    on -= 1
                off = i                                     # walk forward through the soft decay
                while off < j and soft[off]:
                    off += 1
                cut_a = max(off + 4, i + int((want - 0.06) * 100))
                cut_b = on - 6                              # 60 ms of room tone before the onset
                if cut_b > cut_a:
                    keep[cut_a:cut_b] = False
            i = j
        else:
            i += 1

    # Kept runs -> frame segments.
    segs = []
    i = 0
    while i < len(keep):
        if keep[i]:
            j = i
            while j < len(keep) and keep[j]:
                j += 1
            fa, fb = round(i / 100 * FPS), round(j / 100 * FPS)
            # ASR word times can be ~0.2 s early, so only short runs with no word nearby are dropped
            has_word = (j - i) >= 60 or any(i / 100 - 0.3 <= st < j / 100 + 0.1 for st in starts)
            if fb > fa and has_word:                         # drop breaths / noises between phrases
                segs.append([fa, fb])
            i = j
        else:
            i += 1
    # Label each cut: sentence end vs micro trim.
    out = []
    for n, (fa, fb) in enumerate(segs):
        t_end = fb / FPS
        before = [w for w, s in words if s < t_end]
        kind = "sentence" if before and before[-1].endswith((".", "?", "!", ",")) else "micro"
        out.append([fa, fb, kind])
    json.dump({"fps": FPS, "segments": out}, open(f"{work}/edl.json", "w"))
    dur = sum(b - a for a, b, _ in out) / FPS
    print(f"source {T:.1f}s -> edited {dur:.1f}s in {len(out)} segments")
    for a, b, k in out:
        print(f"{a / FPS:7.2f}-{b / FPS:7.2f} {k}")


if __name__ == "__main__":
    main(sys.argv[1])

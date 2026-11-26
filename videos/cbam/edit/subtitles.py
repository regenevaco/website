"""English subtitles (SRT) for the assembled CBAM video.

    python3 subtitles.py <cfg.json> <out.srt>

cfg.json (same as assemble.py) plus: "script" (script.json), "wordtimes" (narration word times per line,
from Parakeet), "cam_words" (ASR words per clip: {clip: [[word, start_s], ...]}), "transcripts"
(corrected on-camera text per clip), optional "outro_words" ([[word, start_s], ...]) and "outro_text".

Narration cues use the script's display text, timed from the narration's own word timings.
On-camera cues use the corrected transcript, aligned word by word to the ASR timings, then mapped through
the cut list (trimmed pauses) onto the final timeline.
"""
import difflib
import json
import re
import sys

FPS = 30
MAXC = 42          # characters per subtitle row (two rows per cue)


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def split_cues(text):
    """Split text into cues of at most two rows of MAXC characters, preferring sentence and clause breaks."""
    words = text.split()
    cues, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if len(trial) > 2 * MAXC - 4 and cur:
            # break at the last clause boundary if it leaves a reasonably full cue
            cut = max([i + 1 for i, x in enumerate(cur) if re.search(r"[,;:]$", x) and i + 1 >= 0.45 * len(cur)],
                      default=len(cur))
            cues.append(cur[:cut])
            cur = cur[cut:] + [w]
        else:
            cur.append(w)
            if re.search(r"[.?!]$", w) and len(" ".join(cur)) > 30:
                cues.append(cur)
                cur = []
    if cur:
        cues.append(cur)
    # avoid one- or two-word orphans
    out = []
    for c in cues:
        if out and len(c) <= 2 and len(" ".join(out[-1] + c)) <= 2 * MAXC + 6:
            out[-1] += c
        else:
            out.append(c)
    return out


def two_rows(words):
    s = " ".join(words)
    if len(s) <= MAXC:
        return s
    best, bi = 1e9, 1
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = max(len(a), len(b)) + (0 if re.search(r"[,.:;?!]$", words[i - 1]) else 6)
        if score < best:
            best, bi = score, i
    return " ".join(words[:bi]) + "\n" + " ".join(words[bi:])


def ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def align_times(text_words, asr):
    """Start time for every word of the corrected text, from ASR words (difflib alignment + interpolation)."""
    a = [norm(w) for w in text_words]
    b = [norm(w) for w, _ in asr]
    times = [None] * len(a)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = asr[blk.b + k][1]
    known = [i for i, t in enumerate(times) if t is not None]
    for i in range(len(times)):
        if times[i] is None:
            lo = max([k for k in known if k < i], default=None)
            hi = min([k for k in known if k > i], default=None)
            if lo is not None and hi is not None:
                times[i] = times[lo] + (times[hi] - times[lo]) * (i - lo) / (hi - lo)
            elif lo is not None:
                times[i] = times[lo] + 0.3 * (i - lo)
            else:
                times[i] = times[hi] - 0.3 * (hi - i)
    return times


def src_to_out(t, segs, out0):
    """Source time -> final timeline time through the cut list (a time in a removed gap snaps forward)."""
    acc = 0
    for a, b, _ in segs:
        if t < b / FPS:
            return out0 + (acc + max(0, t - a / FPS) * FPS) / FPS
        acc += b - a
    return out0 + acc / FPS


def main(cfg_path, out):
    cfg = json.load(open(cfg_path))
    plan = json.load(open(f"{cfg['work']}/plan.json"))
    script = {s["id"]: s for s in json.load(open(cfg["script"]))["scenes"]}
    timing = {s["id"]: s for s in json.load(open(cfg["timing"]))["scenes"]}
    wt = json.load(open(cfg["wordtimes"]))
    cam_words = json.load(open(cfg["cam_words"]))
    trans = json.load(open(cfg["transcripts"]))
    cues = []                                                    # (start, end_limit, text)
    for s in plan["segments"]:
        t0 = s["start"] / FPS
        seg_end = (s["start"] + s["frames"]) / FPS
        if s["kind"] == "exp":
            sc, tm = script[s["name"]], timing[s["name"]]
            for li, (ln, lt) in enumerate(zip(sc["lines"], tm["lines"])):
                heard = wt.get(f"{s['name']}/{li}") or [["x", 0.0]]
                ls = t0 + lt["start"]
                # char-fraction -> time map from the heard words
                tot = sum(len(w) + 1 for w, _ in heard)
                marks, c = [], 0
                for w, t in heard:
                    marks.append((c / tot, t))
                    c += len(w) + 1
                marks.append((1.0, lt["dur"]))

                def at(frac):
                    for (f0, a), (f1, b) in zip(marks, marks[1:]):
                        if frac <= f1:
                            return a + (b - a) * ((frac - f0) / max(1e-6, f1 - f0))
                    return lt["dur"]
                text = ln["text"]
                n = len(text)
                pos = 0
                parts = split_cues(text)
                for k, ws in enumerate(parts):
                    piece = " ".join(ws)
                    start = ls + at(pos / n)
                    pos += len(piece) + 1
                    end = ls + (at(min(1, pos / n)) if k < len(parts) - 1 else lt["dur"]) + 0.15
                    cues.append([start, end, two_rows(ws)])
        elif s["kind"] == "cam":
            segs = json.load(open(f"{cfg['edl']}/{s['name']}.json"))["segments"]
            words = trans[s["name"]].split()
            times = align_times(words, cam_words[s["name"]])
            i = 0
            for ws in split_cues(trans[s["name"]]):
                st = src_to_out(times[i], segs, t0)
                j = i + len(ws)
                en = src_to_out(times[j], segs, t0) if j < len(times) else seg_end - 0.3
                cues.append([max(t0, st), min(seg_end, en), two_rows(ws)])
                i = j
        elif s["name"] == "outro" and cfg.get("outro_text"):
            words = cfg["outro_text"].split()
            times = align_times(words, cfg.get("outro_words", [["x", 0.5]]))
            cues.append([t0 + times[0], seg_end - 0.5, two_rows(words)])
    cues.sort()
    with open(out, "w") as f:
        for k, (a, b, t) in enumerate(cues):
            nxt = cues[k + 1][0] if k + 1 < len(cues) else b
            b = min(b, nxt - 0.04, a + max(1.2, len(t) * 0.075 + 1.4))
            b = max(b, a + 0.8)
            f.write(f"{k + 1}\n{ts(a)} --> {ts(b)}\n{t}\n\n")
    print(out, len(cues), "cues")


if __name__ == "__main__":
    main(*sys.argv[1:3])

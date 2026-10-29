"""Synthesize the narration and compute the video timeline.

Usage: python3 build_audio.py <kokoro-model.onnx> <voices.bin> <out_dir>
       python3 build_audio.py --captions-only <timing.json> <out_dir>

Writes into <out_dir>:
  narration.wav   full voice-over track (24 kHz mono)
  timing.json     scene/line start times used by scenes.html
  captions.srt    YouTube-ready subtitles
  chapters.txt    YouTube chapter timestamps
"""
import json
import math
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 24000
LEAD_IN = 1.4        # first scene: let the title land before speaking
SCENE_PAD_IN = 0.7   # silence at the start of every other scene
LINE_GAP = 0.45      # pause between lines inside a scene
SCENE_PAD_OUT = 1.0  # hold after the last line of a scene
OUTRO_HOLD = 4.0     # end card
SPEED = 1.06         # slightly brisker than default for YouTube pacing


def trim(audio, thresh=0.003):
    idx = np.where(np.abs(audio) > thresh)[0]
    if len(idx) == 0:
        return audio
    return audio[max(0, idx[0] - 240): idx[-1] + 480]


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def split_caption(text, max_chars=84):
    """Break a line into balanced subtitle chunks, preferring punctuation breaks."""
    n = math.ceil(len(text) / max_chars)
    if n <= 1:
        return [text]
    # candidate break points: index of each space
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    cuts, prev = [], 0
    for k in range(1, n):
        ideal = len(text) * k / n
        best = min((sp for sp in spaces if sp > prev),
                   key=lambda sp: abs(sp - ideal) - (14 if text[sp - 1] in ",.:;?" else 0))
        cuts.append(best)
        prev = best
    bounds = [0] + cuts + [len(text)]
    return [text[a:b].strip() for a, b in zip(bounds, bounds[1:])]


def write_text_tracks(script, timing, out):
    """captions.srt and chapters.txt from the script and computed timeline."""
    srt = []
    for scene, st in zip(script["scenes"], timing["scenes"]):
        for line, lt in zip(scene["lines"], st["lines"]):
            # Spread the caption chunks over the line by character share.
            chunks = split_caption(line["text"])
            total = sum(len(c) for c in chunks)
            ct = st["start"] + lt["start"]
            for c in chunks:
                cd = lt["dur"] * len(c) / total
                srt.append((ct, ct + cd, c))
                ct += cd
    with open(os.path.join(out, "captions.srt"), "w") as f:
        for i, (a, b, c) in enumerate(srt, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{c}\n\n")
    with open(os.path.join(out, "chapters.txt"), "w") as f:
        for st in timing["scenes"]:
            m, sec = divmod(int(st["start"]), 60)
            f.write(f"{m}:{sec:02} {st['chapter']}\n")


def main():
    script = json.load(open(os.path.join(HERE, "script.json")))
    if sys.argv[1] == "--captions-only":
        timing, out = json.load(open(sys.argv[2])), sys.argv[3]
        write_text_tracks(script, timing, out)
        return
    model, voices, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    tts = Kokoro(model, voices)

    track, t = [], 0.0
    timing = {"scenes": []}
    for si, scene in enumerate(script["scenes"]):
        start = t
        pad = LEAD_IN if si == 0 else SCENE_PAD_IN
        track.append(np.zeros(int(pad * SR), dtype=np.float32))
        t += pad
        lines = []
        for li, line in enumerate(scene["lines"]):
            audio, sr = tts.create(line["say"], voice=script["voice"], speed=SPEED, lang="en-us")
            assert sr == SR
            audio = trim(audio.astype(np.float32))
            dur = len(audio) / SR
            lines.append({"start": round(t - start, 3), "dur": round(dur, 3)})
            track.append(audio)
            t += dur
            if li < len(scene["lines"]) - 1:
                track.append(np.zeros(int(LINE_GAP * SR), dtype=np.float32))
                t += LINE_GAP
            print(f"{scene['id']:>15} line {li}: {dur:5.2f}s", flush=True)
        hold = OUTRO_HOLD if si == len(script["scenes"]) - 1 else SCENE_PAD_OUT
        track.append(np.zeros(int(hold * SR), dtype=np.float32))
        t += hold
        timing["scenes"].append({"id": scene["id"], "chapter": scene["chapter"],
                                 "start": round(start, 3), "dur": round(t - start, 3), "lines": lines})

    timing["total"] = round(t, 3)
    voice = np.concatenate(track)
    sf.write(os.path.join(out, "narration.wav"), voice, SR)
    json.dump(timing, open(os.path.join(out, "timing.json"), "w"), indent=1)
    write_text_tracks(script, timing, out)
    print(f"total {t:.1f}s")


if __name__ == "__main__":
    main()

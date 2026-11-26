"""Build the explainer timing for the CBAM scenes.

    python3 mktiming.py <script.json> <voice_dir> <out timing.json>

Uses the real narration line WAVs when they exist, otherwise estimates the
length from the word count, so layouts can be checked before the voice is done.
Each scene is rendered on its own, so every scene's times are local (start 0).
"""
import json
import os
import sys
import wave

PAD_IN = 1.3     # chapter card before the first line
LINE_GAP = 0.45  # pause between lines
PAD_OUT = 0.9    # hold after the last line
# extra hold after a line, for screen captures and big reveals: (scene, line) -> seconds
EXTRA = {("basics", 8): 2.6, ("cost", 2): 1.2, ("cost", 3): 0.4, ("global", 10): 0.6, ("regeneva", 3): 1.6,
         ("checklist", 5): 1.4}
WPS = 2.45       # estimate only


def wav_len(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def main(script_path, voice_dir, out):
    script = json.load(open(script_path))
    scenes, real = [], 0
    for sc in script["scenes"]:
        t, lines = PAD_IN, []
        for i, ln in enumerate(sc["lines"]):
            p = os.path.join(voice_dir, "lines", f"{sc['id']}_{i:02}.wav")
            if os.path.exists(p):
                d = wav_len(p)
                real += 1
            else:
                d = len(ln["text"].split()) / WPS
            lines.append({"start": round(t, 3), "dur": round(d, 3)})
            t += d + EXTRA.get((sc["id"], i), 0)
            t += LINE_GAP if i < len(sc["lines"]) - 1 else PAD_OUT
        scenes.append({"id": sc["id"], "chapter": sc["chapter"], "tone": sc["tone"], "start": 0,
                       "dur": round(t, 3), "lines": lines})
    json.dump({"scenes": scenes, "real_lines": real}, open(out, "w"), indent=1)
    print(f"{real} real lines; " + ", ".join(f"{s['id']} {s['dur']:.1f}s" for s in scenes))


if __name__ == "__main__":
    main(*sys.argv[1:4])

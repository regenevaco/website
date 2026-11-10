"""Subtitles + chapters for the opener + explainer cut.

    python3 captions.py <final_words.json> <explainer.srt> <explainer_timing.json> <offset_s> <out_dir>

Opener cues are the presenter's exact words (spelling of names and acronyms normalised), timed from
ASR word timestamps on the final edited timeline. Explainer cues and chapters are shifted by offset_s
(opener length minus the transition overlap).
"""
import json
import re
import sys

# Exact spoken text, one cue per line: (first word, approximate start on the final timeline, text).
OPENER = [
    ("four", 0.2, "490 Indian factories got a new target."),
    ("Guess", 4.2, "Guess what?"),
    ("Not", 5.1, "Not a production target, or not a revenue target."),
    ("It's", 8.1, "It's a carbon target."),
    ("Hi", 9.8, "Hi all, this is Surya Narayan Kar."),
    ("Welcome", 12.0, "Welcome to another ESG and Sustainability Explainer by ReGeneva."),
    ("The", 15.7, "The mechanism is very simple."),
    ("You", 18.3, "You beat the target, and every tonne of greenhouse gas emission"),
    ("you", 22.5, "you are saving can become a certificate, and you can sell."),
    ("Miss", 26.0, "Miss it, you need to pay the price and buy the certificate."),
    ("And", 30.0, "And this mechanism is not restricted to only India."),
    ("Europe", 34.0, "Europe has its own carbon tax, known as"),
    ("Carbon", 37.5, "Carbon Border Adjustment Mechanism, CBAM carbon tax."),
    ("UK", 41.0, "UK also recognised India's CCTS, right?"),
    ("That", 45.9, "That is, Carbon Credit Trading Scheme."),
    ("Every", 48.3, "Every CFO, every plant head, ESG sustainability team member"),
    ("is", 52.4, "is having one question right now in India."),
    ("At", 55.1, "At the end of the year, whether we'll be having the certificates"),
    ("or", 59.1, "or we need to pay the bill?"),
    ("We'll", 61.3, "We'll be having the credit, or we need to pay the bill?"),
    ("This", 63.4, "This is the mega question that every Indian factory is now hovering around."),
    ("In", 67.6, "In this video, we will be understanding about"),
    ("India's", 70.4, "India's Carbon Credit Trading Scheme:"),
    ("what", 72.8, "what it is, where it is currently standing,"),
    ("what", 75.5, "what are the opportunities around it."),
    ("Stay", 78.0, "Stay till the end, because at the end"),
    ("we", 80.5, "we will be unveiling about the opportunity"),
    ("for", 82.5, "for all the ESG and sustainable professionals"),
    ("and", 84.9, "and the other people who are working in"),
    ("ESG", 86.9, "ESG, sustainability or climate change field."),
    ("So", 89.5, "So, without further much delay,"),
    ("let's", 91.0, "let's begin with the example of two cement plants."),
]


def ts(t):
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(p):
    out = []
    for block in open(p, encoding="utf-8").read().strip().split("\n\n"):
        lines = block.strip().splitlines()
        a, b = re.findall(r"(\d+):(\d+):(\d+),(\d+)", lines[1])
        to_s = lambda x: int(x[0]) * 3600 + int(x[1]) * 60 + int(x[2]) + int(x[3]) / 1000
        out.append((to_s(a), to_s(b), "\n".join(lines[2:])))
    return out


def main(words_p, srt_p, timing_p, offset, out_dir):
    offset = float(offset)
    words = json.load(open(words_p))
    norm = lambda w: re.sub(r"[^a-z']", "", w.lower())
    # Each cue starts on its first word nearest the hint (ASR spells some words differently, e.g. "EAZ").
    starts = []
    for key, hint, _ in OPENER:
        cand = [t for w, t in words if norm(w) == norm(key) and abs(t - hint) < 1.0]
        starts.append(min(cand, key=lambda t: abs(t - hint)) if cand else min((t for _, t in words), key=lambda t: abs(t - hint)))
    end_all = words[-1][1] + 0.6
    cues = []
    for i, (_, _, text) in enumerate(OPENER):
        a = starts[i] - 0.05
        b = (starts[i + 1] - 0.08) if i + 1 < len(OPENER) else end_all
        cues.append((a, b, text))
    for a, b, text in parse_srt(srt_p):
        cues.append((a + offset, b + offset, text))
    with open(f"{out_dir}/captions.srt", "w", encoding="utf-8") as f:
        for n, (a, b, text) in enumerate(cues, 1):
            f.write(f"{n}\n{ts(a)} --> {ts(b)}\n{text}\n\n")

    timing = json.load(open(timing_p))
    chapters = [(0.0, "Intro: credits or a bill?")]
    for sc in timing["scenes"]:
        chapters.append((sc["start"] + offset, sc["chapter"]))
    with open(f"{out_dir}/chapters.txt", "w") as f:
        for t, name in chapters:
            t = int(t)
            f.write(f"{t // 60}:{t % 60:02d} {name}\n")
    for i, (a, _, t) in enumerate(cues[:len(OPENER)]):
        print(f"{a:6.2f} {t}")
    print(open(f"{out_dir}/chapters.txt").read())


if __name__ == "__main__":
    main(*sys.argv[1:6])

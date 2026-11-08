"""Generate the narration in Surya's Clone Voice and compute the video timeline.

    python3 build_voice.py <out_dir>                 # full narration
    python3 build_voice.py <out_dir> --only hook     # one scene (for previews)
    python3 build_voice.py <out_dir> --redo close:4  # regenerate listed lines, then re-assemble
    python3 build_voice.py <out_dir> --assemble      # re-assemble narration/timing from lines/*.wav
    python3 build_voice.py <out_dir> --captions-only # rebuild SRT/chapters from timing.json

Configuration comes from a profile in profiles/ plus environment variables:
    SURYA_VOICE_MODELS  folder holding the ZipVoice, Vocos and Parakeet model files
    SURYA_VOICE_REF_DIR folder holding the profile's style reference clips (kept outside the repo)
    VOICE_PROFILE       profile name in profiles/ (default: surya-indian-accent-original-voice-clone)

Each chunk is checked with an ASR model and re-generated with a new seed when the
transcript drifts from the script, so misread words are caught automatically.
"""
import difflib
import json
import math
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from zipclone import ZipClone, SR  # noqa: E402

SCRIPT = os.path.join(HERE, "..", "script", "script.json")
PROFILE = json.load(open(os.path.join(HERE, "profiles", os.environ.get(
    "VOICE_PROFILE", "surya-indian-accent-original-voice-clone") + ".json")))
LEAD_IN, SCENE_PAD_IN, CHUNK_GAP, LINE_GAP, SCENE_PAD_OUT, OUTRO_HOLD = 1.6, 0.8, 0.22, 0.5, 1.1, 6.0
MIN_SIMILARITY, MAX_TRIES = 0.8, 4


def chunks(say):
    """Group sentences so each generation is 8-35 words (very short prompts sound clipped)."""
    sents = re.split(r"(?<=[.?!])\s+", say.strip())
    out, cur = [], ""
    for s in sents:
        cur = f"{cur} {s}".strip()
        if len(cur.split()) >= 8:
            out.append(cur)
            cur = ""
    if cur:
        if out and len(cur.split()) < 5 and len(out[-1].split()) + len(cur.split()) <= 35:
            out[-1] = f"{out[-1]} {cur}"
        else:
            out.append(cur)
    return out


def norm(t):
    return re.sub(r"[^a-z0-9 ]", " ", t.lower().replace("-", " ")).split()


class Checker:
    def __init__(self, models):
        import sherpa_onnx
        d = os.path.join(models, "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8")
        self.rec = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=f"{d}/encoder.int8.onnx", decoder=f"{d}/decoder.int8.onnx",
            joiner=f"{d}/joiner.int8.onnx", tokens=f"{d}/tokens.txt", model_type="nemo_transducer")

    def transcribe(self, wav):
        with tempfile.NamedTemporaryFile(suffix=".wav") as a, tempfile.NamedTemporaryFile(suffix=".wav") as b:
            sf.write(a.name, wav, SR)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.name, "-ar", "16000", b.name], check=True)
            x, sr = sf.read(b.name, dtype="float32")
        st = self.rec.create_stream()
        st.accept_waveform(sr, x)
        self.rec.decode_stream(st)
        return st.result.text


def number_words(t):
    # ASR writes digits; compare against a spelled-out form of the script.
    small = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
    tens = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()

    def say(n):
        if n < 20:
            return small[n]
        if n < 100:
            return tens[n // 10] + ("" if n % 10 == 0 else " " + small[n % 10])
        if n < 1000:
            return small[n // 100] + " hundred" + ("" if n % 100 == 0 else " and " + say(n % 100))
        return say(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + say(n % 1000))

    return re.sub(r"\d+", lambda m: say(int(m.group())) if len(m.group()) < 7 else m.group(), t.replace(",", ""))


def similarity(script_text, asr_text):
    a, b = norm(script_text), norm(number_words(asr_text))
    return difflib.SequenceMatcher(None, a, b).ratio()


def trim(w, thresh=0.004):
    idx = np.where(np.abs(w) > thresh)[0]
    return w if len(idx) == 0 else w[max(0, idx[0] - 240): idx[-1] + 720]


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def split_caption(text, max_chars=80):
    n = math.ceil(len(text) / max_chars)
    if n <= 1:
        return [text]
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    cuts, prev = [], 0
    for k in range(1, n):
        ideal = len(text) * k / n
        best = min((sp for sp in spaces if sp > prev),
                   key=lambda sp: abs(sp - ideal) - (16 if text[sp - 1] in ",.:;?" else 0))
        cuts.append(best)
        prev = best
    b = [0] + cuts + [len(text)]
    return [text[x:y].strip() for x, y in zip(b, b[1:])]


def write_text_tracks(script, timing, out):
    srt = []
    for scene, st in zip(script["scenes"], timing["scenes"]):
        for line, lt in zip(scene["lines"], st["lines"]):
            parts = split_caption(line["text"])
            total = sum(len(p) for p in parts)
            t = st["start"] + lt["start"]
            for p in parts:
                d = lt["dur"] * len(p) / total
                srt.append((t, t + d, p))
                t += d
    with open(os.path.join(out, "captions.srt"), "w") as f:
        for i, (a, b, c) in enumerate(srt, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{c}\n\n")
    with open(os.path.join(out, "chapters.txt"), "w") as f:
        for st in timing["scenes"]:
            m, s = divmod(int(st["start"]), 60)
            f.write(f"{m}:{s:02} {st['chapter']}\n")


def load_voice():
    models = os.environ["SURYA_VOICE_MODELS"]
    refs = os.environ[PROFILE["reference_dir_env"]]
    m = PROFILE["model"]
    styles = PROFILE["styles"]
    first = styles[PROFILE["default_style"]]
    voice = ZipClone(os.path.join(models, m["dir"]), os.path.join(models, m["vocoder"]),
                     os.path.join(models, m["tokens"]), os.path.join(refs, first["file"]), first["text"],
                     encoder=m["encoder"], decoder=m["decoder"])
    for name, st in styles.items():
        voice.add_prompt(name, os.path.join(refs, st["file"]), st["text"])
    return voice, Checker(models)


def generate_line(voice, checker, scene, li, line, out, report):
    g = PROFILE["generation"]
    pieces = []
    for ci, chunk in enumerate(chunks(line["say"])):
        best = None
        for attempt in range(MAX_TRIES):
            style = line.get("style", PROFILE["default_style"])
            w = trim(voice.say(chunk, speed=PROFILE["style_speed"].get(style, 1.0), prompt=style,
                               steps=g["steps"], guidance=g["guidance"],
                               t_shift=g["t_shift"], seed=1000 * li + 10 * ci + attempt))
            heard = checker.transcribe(w)
            sim = similarity(re.sub(r"\[\[.*?\]\]", "", chunk), heard)
            if best is None or sim > best[0]:
                best = (sim, w, heard, attempt)
            if sim >= MIN_SIMILARITY:
                break
        sim, w, heard, attempt = best
        report[f"{scene['id']}/{li}/{ci}"] = {"chunk": chunk, "heard": heard, "similarity": round(sim, 3),
                                             "tries": attempt + 1}
        print(f"{scene['id']}/{li}.{ci} sim={sim:.2f} tries={attempt + 1}", flush=True)
        pieces += [w, np.zeros(int(CHUNK_GAP * SR), np.float32)]
    sf.write(os.path.join(out, "lines", f"{scene['id']}_{li:02}.wav"), np.concatenate(pieces[:-1]), SR)


def assemble(script, out):
    """Build narration.wav, timing.json, captions and chapters from the per-line WAVs."""
    track, t, timing = [], 0.0, {"scenes": []}
    for si, scene in enumerate(script["scenes"]):
        start = t
        pad = LEAD_IN if si == 0 else SCENE_PAD_IN
        track.append(np.zeros(int(pad * SR), np.float32))
        t += pad
        lines = []
        for li in range(len(scene["lines"])):
            lw, sr = sf.read(os.path.join(out, "lines", f"{scene['id']}_{li:02}.wav"), dtype="float32")
            lines.append({"start": round(t - start, 3), "dur": round(len(lw) / SR, 3)})
            track.append(lw)
            t += len(lw) / SR
            if li < len(scene["lines"]) - 1:
                track.append(np.zeros(int(LINE_GAP * SR), np.float32))
                t += LINE_GAP
        hold = OUTRO_HOLD if si == len(script["scenes"]) - 1 else SCENE_PAD_OUT
        track.append(np.zeros(int(hold * SR), np.float32))
        t += hold
        timing["scenes"].append({"id": scene["id"], "chapter": scene["chapter"], "tone": scene["tone"],
                                 "start": round(start, 3), "dur": round(t - start, 3), "lines": lines})
    timing["total"] = round(t, 3)
    sf.write(os.path.join(out, "narration.wav"), np.concatenate(track), SR)
    json.dump(timing, open(os.path.join(out, "timing.json"), "w"), indent=1)
    write_text_tracks(script, timing, out)
    print(f"total {t:.1f}s")


def main():
    out = sys.argv[1]
    os.makedirs(os.path.join(out, "lines"), exist_ok=True)
    script = json.load(open(SCRIPT))
    if "--captions-only" in sys.argv:
        write_text_tracks(script, json.load(open(os.path.join(out, "timing.json"))), out)
        return
    qa_path = os.path.join(out, "voice_qa.json")
    report = json.load(open(qa_path)) if os.path.exists(qa_path) else {}
    if isinstance(report, list):  # older list format: re-key by scene/line/chunk
        keyed, seen = {}, {}
        for r in report:
            k = (r["scene"], r["line"])
            ci = seen.get(k, 0)
            seen[k] = ci + 1
            keyed[f"{r['scene']}/{r['line']}/{ci}"] = {x: r[x] for x in ("chunk", "heard", "similarity", "tries")}
        report = keyed
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    redo = sys.argv[sys.argv.index("--redo") + 1].split(",") if "--redo" in sys.argv else None
    if "--assemble" not in sys.argv:
        voice, checker = load_voice()
        for scene in script["scenes"]:
            if only and scene["id"] != only:
                continue
            for li, line in enumerate(scene["lines"]):
                if redo and f"{scene['id']}:{li}" not in redo:
                    continue
                generate_line(voice, checker, scene, li, line, out, report)
        json.dump(report, open(qa_path, "w"), indent=1, ensure_ascii=False)
    if only is None:
        assemble(script, out)


if __name__ == "__main__":
    main()

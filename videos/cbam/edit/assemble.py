"""Assemble the CBAM explainer: brand intro, on-camera clips, explainer chapters, brand outro.

    python3 assemble.py plan  <cfg.json>            -> <work>/plan.json, chapters.txt
    python3 assemble.py audio <cfg.json>            -> <work>/mix.wav (-14 LUFS, -1.5 dBTP)
    python3 assemble.py video <cfg.json> <part> <n_parts>  -> <work>/v_part<k>.mp4 (frame range of the master)
    python3 assemble.py mux   <cfg.json> <out.mp4>  -> joins the parts and adds the mix

cfg.json: {"work": dir, "raw": dir with ReGeneva_intro/outro.mp4, "edl": dir, "camaudio": dir, "cam": dir with
comp mp4s, "scenes": dir with <scene>.mp4, "timing": explainer timing.json, "lines": narration lines dir,
"overlays": dir with lower/ and sub/ PNG frames, "sfx": dir with click/ding/whoosh.wav, "music_lib": path to
videos/india-ccts/audio}

Every boundary is a 0.4 s transition (video only; audio is layered, never cross-faded, so no word is cut).
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

FPS, XF = 30, 12                      # transition length in frames
SR = 48000
SEQ = [("intro", "brand"), ("CBAM_01_cold-open", "cam"), ("basics", "exp"), ("CBAM_02_importer-pays", "cam"),
       ("timeline", "exp"), ("CBAM_03_rules-kept-moving", "cam"), ("who", "exp"), ("cost", "exp"),
       ("CBAM_04_data-is-money", "cam"), ("global", "exp"), ("CBAM_05_debate", "cam"), ("challenges", "exp"),
       ("regeneva", "exp"), ("checklist", "exp"), ("CBAM_06_close-CTA", "cam"), ("outro", "brand")]
CHAPTERS = {"CBAM_01_cold-open": "CBAM is live: why it matters now",
            "basics": "CBAM in 90 seconds",
            "CBAM_02_importer-pays": "The importer pays, but the exporter feels it",
            "timeline": "The timeline: how CBAM kept changing",
            "CBAM_03_rules-kept-moving": "It's not you: the rules kept moving",
            "who": "Who has to comply",
            "cost": "What it costs: a worked example",
            "CBAM_04_data-is-money": "Your data is now worth money",
            "global": "The global ripple",
            "CBAM_05_debate": "The debate: climate tool or trade barrier?",
            "challenges": "The five real challenges",
            "regeneva": "How ReGeneva helps",
            "checklist": "Your CBAM readiness checklist",
            "CBAM_06_close-CTA": "Wrap-up and next steps"}
TRANSITION = {"brand": "fade"}       # into/out of the brand clips; everything else slides
LOWER_AT = ("CBAM_01_cold-open", 1.5)
SUB_AT = [("CBAM_03_rules-kept-moving", 4.0), ("CBAM_05_debate", 4.0)]


def nframes(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v",
                          "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return int(out.strip())


def plan(cfg):
    timing = {s["id"]: s for s in json.load(open(cfg["timing"]))["scenes"]}
    segs, t = [], 0
    for i, (name, kind) in enumerate(SEQ):
        if kind == "brand":
            n = nframes(f"{cfg['raw']}/ReGeneva_{name}.mp4")
        elif kind == "cam":
            n = sum(b - a for a, b, _ in json.load(open(f"{cfg['edl']}/{name}.json"))["segments"])
        else:
            n = int(np.ceil(timing[name]["dur"] * FPS))
        start = 0 if i == 0 else t - XF
        segs.append({"name": name, "kind": kind, "start": start, "frames": n})
        t = start + n
    total = t
    lookup = {s["name"]: s for s in segs}
    lower = lookup[LOWER_AT[0]]["start"] + round(LOWER_AT[1] * FPS)
    subs = [lookup[n]["start"] + round(o * FPS) for n, o in SUB_AT]
    p = {"segments": segs, "total": total, "lower": lower, "subs": subs}
    json.dump(p, open(f"{cfg['work']}/plan.json", "w"), indent=1)
    with open(f"{cfg['work']}/chapters.txt", "w") as f:
        for s in segs:
            if s["name"] in CHAPTERS:
                sec = 0 if s["name"] == "CBAM_01_cold-open" else (s["start"] + XF // 2) // FPS
                f.write(f"{sec // 60}:{sec % 60:02d} {CHAPTERS[s['name']]}\n")
    print(f"total {total / FPS:.1f}s ({total} frames)")
    for s in segs:
        print(f"{s['start'] / FPS:8.2f}  {s['frames'] / FPS:7.2f}s  {s['name']}")
    return p


# ---------------------------------------------------------------- audio
def ff(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args, check=True)


def read48(path):
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    if sr != SR:
        tmp = path + ".48k.wav"
        ff(["-i", path, "-ar", str(SR), "-c:a", "pcm_f32le", tmp])
        x, _ = sf.read(tmp, dtype="float32", always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    return x


def lufs_norm(path, out, target):
    ff(["-i", path, "-af", f"loudnorm=I={target}:TP=-2:LRA=11", "-ar", str(SR), "-c:a", "pcm_f32le", out])


def narration(cfg, scene, work):
    """One explainer scene's narration on its local clock, polished like the CCTS explainer voice."""
    sc = {s["id"]: s for s in json.load(open(cfg["timing"]))["scenes"]}[scene]
    n = int(np.ceil(sc["dur"] * SR)) + SR
    buf = np.zeros((n, 2), np.float32)
    for li, ln in enumerate(sc["lines"]):
        w = read48(f"{cfg['lines']}/{scene}_{li:02}.wav")
        a = int(ln["start"] * SR)
        buf[a:a + len(w)] += w[:n - a]
    raw = f"{work}/nar_{scene}_raw.wav"
    sf.write(raw, buf, SR, subtype="FLOAT")
    pol = f"{work}/nar_{scene}.wav"
    ff(["-i", raw, "-af", "highpass=f=75,lowpass=f=15000,deesser=i=0.35,"
        "acompressor=threshold=-22dB:ratio=2.8:attack=6:release=140:makeup=2,"
        "equalizer=f=180:t=q:w=1:g=1.5,equalizer=f=3200:t=q:w=1.4:g=2.2",
        "-ar", str(SR), "-c:a", "pcm_f32le", pol])
    return pol


def build_music(cfg, p, work):
    sys.path.insert(0, cfg["music_lib"])
    import build_music as bm                                    # CCTS synthesized palette (no licensing)
    total = p["total"] / FPS + 1.0
    n = int(total * SR)
    music = np.zeros((n, 2))
    segs = [s for s in p["segments"] if s["kind"] != "brand"]
    tone = {s["id"]: s["tone"] for s in json.load(open(cfg["timing"]))["scenes"]}
    xf = 1.6
    for i, s in enumerate(segs):
        kind = "close" if s["name"] in ("checklist", "CBAM_06_close-CTA") else tone.get(s["name"], "light")
        start = max(0, s["start"] / FPS - xf / 2)
        end = min(total, (s["start"] + s["frames"]) / FPS + xf / 2)
        seg = bm.section(kind, end - start, i)
        gain = 0.7 if s["kind"] == "cam" else 1.0              # lighter under the presenter
        fade = np.ones(len(seg))
        f = int(xf * SR)
        fade[:f] = np.linspace(0, 1, f)
        fade[-f:] *= np.linspace(1, 0, f)
        a = int(start * SR)
        music[a:a + len(seg)] += seg * fade[:, None] * gain
    music = bm.reverb(music)
    music /= np.max(np.abs(music)) + 1e-9
    out = f"{work}/music.wav"
    sf.write(out, (music * 0.85).astype(np.float32), SR)
    return out


def audio(cfg):
    p = json.load(open(f"{cfg['work']}/plan.json"))
    work = cfg["work"]
    total = int((p["total"] / FPS + 1) * SR)
    voice = np.zeros((total, 2), np.float32)
    brand = np.zeros((total, 2), np.float32)
    sfx = np.zeros((total, 2), np.float32)
    for s in p["segments"]:
        a = int(s["start"] / FPS * SR)
        if s["kind"] == "brand":
            src = f"{work}/brand_{s['name']}.wav"
            ff(["-i", f"{cfg['raw']}/ReGeneva_{s['name']}.mp4", "-vn", "-ar", str(SR), "-c:a", "pcm_f32le", src + ".tmp.wav"])
            lufs_norm(src + ".tmp.wav", src, -14)
            w = read48(src)
            brand[a:a + len(w)] += w[:total - a]
            continue
        if s["kind"] == "cam":
            src = f"{cfg['camaudio']}/{s['name']}.wav"
        else:
            src = narration(cfg, s["name"], work)
        normed = f"{work}/v_{s['name']}.wav"
        lufs_norm(src, normed, -16)                              # presenter and narration at the same level
        w = read48(normed)
        w = w[:int(s["frames"] / FPS * SR)]
        voice[a:a + len(w)] += w[:total - a]
    # sound design: soft whoosh into every explainer chapter, click + ding on the subscribe reminders
    wh, ck, dg = (read48(f"{cfg['sfx']}/{n}.wav") for n in ("whoosh", "click", "ding"))
    for s in p["segments"][1:]:
        if s["kind"] == "exp":
            a = int((s["start"] / FPS - 0.45) * SR)
            sfx[a:a + len(wh)] += wh * 0.35
    for f0 in p["subs"]:
        for at, snd, g in ((1.15, ck, 0.6), (1.95, dg, 0.45)):
            a = int((f0 / FPS + at) * SR)
            sfx[a:a + len(snd)] += snd[:total - a] * g
    music = read48(build_music(cfg, p, work))[:total]
    for name, arr in (("voice", voice), ("brand", brand), ("sfx", sfx)):
        sf.write(f"{work}/stem_{name}.wav", arr, SR, subtype="FLOAT")
    mpad = np.zeros((total, 2), np.float32)
    mpad[:len(music)] = music
    sf.write(f"{work}/stem_music.wav", mpad, SR, subtype="FLOAT")
    ff(["-i", f"{work}/stem_voice.wav", "-i", f"{work}/stem_music.wav", "-i", f"{work}/stem_sfx.wav",
        "-i", f"{work}/stem_brand.wav", "-filter_complex",
        "[0:a]asplit=2[v][k];[1:a]volume=0.13[m];"
        "[m][k]sidechaincompress=threshold=0.04:ratio=3.5:attack=80:release=900:makeup=1[d];"
        "[2:a]volume=0.8[x];[3:a]volume=1.0[b];"
        "[v][d][x][b]amix=inputs=4:normalize=0:duration=first[pre]",
        "-map", "[pre]", "-c:a", "pcm_f32le", f"{work}/premix.wav"])
    # two-pass loudness: measure, then apply linear normalisation to -14 LUFS, then a true-peak limiter
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{work}/premix.wav", "-af",
                           "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    gain = -14 - float(j["input_i"])
    ff(["-i", f"{work}/premix.wav", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=0:attack=2:release=60",
        "-t", f"{p['total'] / FPS:.3f}", "-ar", str(SR), "-c:a", "pcm_s24le", f"{work}/mix.wav"])
    print("mix gain", round(gain, 2), "dB")


# ---------------------------------------------------------------- video
def video(cfg, part, nparts):
    p = json.load(open(f"{cfg['work']}/plan.json"))
    part, nparts = int(part), int(nparts)
    segs = p["segments"]
    inputs, chains = [], []
    for i, s in enumerate(segs):
        if s["kind"] == "brand":
            src, mat = f"{cfg['raw']}/ReGeneva_{s['name']}.mp4", "bt709"
        elif s["kind"] == "cam":
            src, mat = f"{cfg['cam']}/{s['name']}.mp4", "bt601"
        else:
            src, mat = f"{cfg['scenes']}/{s['name']}.mp4", "bt601"
        inputs += ["-i", src]
        chains.append(f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={FPS},"
                      f"scale=3840:2160:in_color_matrix={mat}:out_color_matrix=bt709:in_range=tv:out_range=tv,"
                      f"trim=end_frame={s['frames']},setpts=PTS-STARTPTS,format=yuv420p[v{i}]")
    last = "v0"
    for i in range(1, len(segs)):
        kind = "fade" if "brand" in (segs[i - 1]["kind"], segs[i]["kind"]) else "smoothleft"
        off = segs[i]["start"] / FPS
        chains.append(f"[{last}][v{i}]xfade=transition={kind}:duration={XF / FPS}:offset={off:.4f}[x{i}]")
        last = f"x{i}"
    k = len(segs)
    inputs += ["-framerate", str(FPS), "-i", f"{cfg['overlays']}/lower/f_%04d.png"]
    chains.append(f"[{k}:v]setpts=PTS-STARTPTS+{p['lower'] / FPS:.4f}/TB[lt]")
    chains.append(f"[{last}][lt]overlay=eof_action=pass:format=auto[o0]")
    last = "o0"
    for j, f0 in enumerate(p["subs"]):
        inputs += ["-framerate", str(FPS), "-i", f"{cfg['overlays']}/sub/f_%04d.png"]
        chains.append(f"[{k + 1 + j}:v]setpts=PTS-STARTPTS+{f0 / FPS:.4f}/TB[sb{j}]")
        chains.append(f"[{last}][sb{j}]overlay=eof_action=pass:format=auto[o{j + 1}]")
        last = f"o{j + 1}"
    per = int(np.ceil(p["total"] / nparts))
    a, b = part * per, min(p["total"], (part + 1) * per)
    chains.append(f"[{last}]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS,format=yuv420p[out]")
    out = f"{cfg['work']}/v_part{part}.mp4"
    ff(inputs + ["-filter_complex", ";".join(chains), "-map", "[out]", "-c:v", "libx264", "-preset", "medium",
                 "-crf", "16", "-pix_fmt", "yuv420p", "-g", "60", "-colorspace", "bt709", "-color_primaries", "bt709",
                 "-color_trc", "bt709", "-color_range", "tv", "-x264-params", "keyint=60:min-keyint=30", out])
    print("part", part, a, b)


def mux(cfg, out):
    w = cfg["work"]
    parts = sorted(f for f in os.listdir(w) if f.startswith("v_part") and f.endswith(".mp4"))
    with open(f"{w}/parts.txt", "w") as f:
        f.writelines(f"file '{w}/{x}'\n" for x in parts)
    ff(["-f", "concat", "-safe", "0", "-i", f"{w}/parts.txt", "-i", f"{w}/mix.wav", "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", out])
    print(out)


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[2]))
    os.makedirs(cfg["work"], exist_ok=True)
    {"plan": lambda: plan(cfg), "audio": lambda: audio(cfg),
     "video": lambda: video(cfg, sys.argv[3], sys.argv[4]), "mux": lambda: mux(cfg, sys.argv[3])}[sys.argv[1]]()

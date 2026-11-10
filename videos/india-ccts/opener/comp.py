"""Stage 5: 4K composite of the to-camera opener.

    python3 comp.py <work_dir> <studio.png> <out.mp4> <k0> <k1> [overlay_dir]

Renders output frames k0..k1-1 of the final (edited, sped-up) timeline:
  source frame (EDL + speed) -> scar repair + light skin retouch -> grade -> 4K matte (guided upsampling)
  -> edge colour unmixing (removes the old white-wall spill) -> composite over the studio -> light wrap
  -> punch-in framing per cut -> overlay graphics -> fine grain -> x264 (BT.601 / tv range, like the explainer)

work_dir needs: raw/IMG_5463.MOV, edl.json, plan.json ({"speed":..., "zoom":[...per segment...]}),
m1/alpha/*.png (1080p mattes) and m1/landmarks.npy.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retouch import fix_scar, soften_skin, soften_under_eyes, tame_hair_shine  # noqa: E402

W, H, FPS = 3840, 2160, 30
TONEMAP = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv")


def timeline(edl, speed, n_out):
    """Output frame -> (source frame, segment index, progress within segment)."""
    ed = []
    for si, (a, b, _) in enumerate(edl):
        for f in range(a, b):
            ed.append((f, si, (f - a) / max(1, b - a - 1)))
    return [ed[min(len(ed) - 1, int(round(k * speed)))] for k in range(n_out)]


def smooth_landmarks(L, r=2):
    out = L.copy()
    for i in range(len(L)):
        w = L[max(0, i - r):i + r + 1]
        good = ~np.isnan(w[:, 0, 0])
        if good.any():
            out[i] = w[good].mean(0)
    # fill missing frames from the nearest detection
    miss = np.isnan(out[:, 0, 0])
    if miss.any():
        idx = np.where(~miss)[0]
        for i in np.where(miss)[0]:
            out[i] = out[idx[np.argmin(abs(idx - i))]]
    return out


_X = np.linspace(0, 1, 4096, dtype=np.float32)
_CURVE = np.clip(_X + 0.06 * np.sin(2 * np.pi * (_X - 0.5)) * _X * (1 - _X) * 2, 0, 1).astype(np.float32)


def grade(x):
    """Gentle presenter grade: a touch warmer, slightly calmer saturation, soft S-curve (via a lookup table)."""
    x = x * np.array([1.02, 1.0, 0.975], np.float32)
    lum = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    x = lum[..., None] + (x - lum[..., None]) * np.float32(0.94)
    idx = (np.clip(x, 0, 1) * 4095).astype(np.int32)
    return _CURVE[idx]


def guided_alpha(a1080, guide):
    a = cv2.resize(a1080, (W, H), interpolation=cv2.INTER_LINEAR)
    g = cv2.cvtColor(guide, cv2.COLOR_RGB2GRAY)
    a = cv2.ximgproc.guidedFilter(g, a, 6, 1e-4)
    return np.clip(a, 0, 1)


def main(work, studio, out, k0, k1, overlay_dir=None):
    k0, k1 = int(k0), int(k1)
    edl = json.load(open(f"{work}/edl.json"))["segments"]
    plan = json.load(open(f"{work}/plan.json"))
    speed, zooms, n_out = plan["speed"], plan["zoom"], plan["frames"]
    tl = timeline(edl, speed, n_out)
    k1 = min(k1, n_out)
    L = smooth_landmarks(np.load(f"{work}/m1/landmarks.npy")[..., :2]) * 2.0   # 1080p -> 4K pixels

    bg = cv2.imread(studio, cv2.IMREAD_UNCHANGED)[..., :3][..., ::-1].astype(np.float32) / 65535.0
    bg = cv2.resize(bg, (W, H), interpolation=cv2.INTER_CUBIC)
    bg_q = cv2.resize(bg, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bg_wrap = cv2.resize(cv2.GaussianBlur(bg_q, (0, 0), 10), (W, H), interpolation=cv2.INTER_LINEAR)

    # Per-segment crop centre: median face centre over the segment, so framing never drifts.
    seg_center = {}
    for si, (a, b, _) in enumerate(edl):
        c = np.nanmedian(L[a:b, 6], axis=0)
        seg_center[si] = c

    need = [tl[k][0] for k in range(k0, k1)]
    uniq = sorted(set(need))
    ranges, s = [], uniq[0]
    for p, q in zip(uniq, uniq[1:] + [None]):
        if q is None or q != p + 1:
            ranges.append((s, p))
            s = q
    sel = "+".join(f"between(n\\,{a}\\,{b})" for a, b in ranges)
    dec = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-i", f"{work}/raw/IMG_5463.MOV", "-map", "0:v:0",
         "-vf", f"fps={FPS},select='{sel}',{TONEMAP},format=gbrpf32le", "-fps_mode", "passthrough",
         "-f", "rawvideo", "-pix_fmt", "gbrpf32le", "-"], stdout=subprocess.PIPE, bufsize=W * H * 12)
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt601:out_range=tv",
         "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
         "-colorspace", "bt470bg", "-color_range", "tv", out], stdin=subprocess.PIPE)

    rng = np.random.default_rng(k0)
    cur_src, cur, ri = -1, None, 0
    fsz = W * H * 4
    for k in range(k0, k1):
        src, si, prog = tl[k]
        while cur_src < src:
            buf = dec.stdout.read(fsz * 3)
            g, b_, r = (np.frombuffer(buf[i * fsz:(i + 1) * fsz], np.float32).reshape(H, W) for i in range(3))
            cur = np.ascontiguousarray(np.stack([r, g, b_], -1))
            cur_src = uniq[ri]
            ri += 1
        img = np.clip(cur, 0, 1)
        lm = L[src]

        # Face: scar repair, light skin and under-eye retouch.
        img = fix_scar(img, lm)
        img = soften_skin(img, lm, 0.35)
        img = soften_under_eyes(img, lm)
        img = grade(img)

        # Matte at 4K, then unmix the old wall colour out of the soft edges.
        a = cv2.imread(f"{work}/m1/alpha/{src:06d}.png", 0).astype(np.float32) / 255.0
        a = guided_alpha(a, img)
        img = tame_hair_shine(img, lm, a)
        a_q = cv2.resize(a, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        img_q = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        wall_w = (cv2.dilate((a_q > 0.02).astype(np.uint8), np.ones((5, 5), np.uint8)) == 0).astype(np.float32)
        old_bg = cv2.GaussianBlur(img_q * wall_w[..., None], (0, 0), 12) / (
            cv2.GaussianBlur(wall_w, (0, 0), 12)[..., None] + 1e-4)
        old_bg = cv2.resize(old_bg, (W, H), interpolation=cv2.INTER_LINEAR)
        edge = (a > 0.01) & (a < 0.985)
        fg = img.copy()
        aa = np.maximum(a[edge], 0.15)[..., None]
        fg[edge] = np.clip((img[edge] - (1 - a[edge])[..., None] * old_bg[edge]) / aa, 0, 1)

        comp = fg * a[..., None] + bg * (1 - a[..., None])
        # Light wrap: a little of the set's light bleeds over the silhouette edge.
        inner = cv2.resize(cv2.GaussianBlur(a_q, (0, 0), 4), (W, H), interpolation=cv2.INTER_LINEAR)
        wrap = (0.45 * a * np.clip(1 - inner, 0, 1))[..., None]
        comp = comp * (1 - wrap) + bg_wrap * wrap

        # Grain: unify the clean CG set with the camera's own noise.
        n = rng.standard_normal((H // 2, W // 2), dtype=np.float32)
        n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)
        comp += (n * (0.004 + 0.006 * (1 - a)))[..., None]

        # Framing: per-segment punch-in with a slow push.
        z = zooms[si] * (1 + 0.02 * prog)
        if z > 1.001:
            cx, cy = seg_center[si]
            cy += 0.08 * H / z                       # keep a little headroom
            cw, ch = W / z, H / z
            x0 = float(np.clip(cx - cw / 2, 0, W - cw))
            y0 = float(np.clip(cy - ch / 2 - 0.12 * ch, 0, H - ch))
            M = np.array([[z, 0, -x0 * z], [0, z, -y0 * z]], np.float32)
            comp = cv2.warpAffine(comp, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)

        if overlay_dir:
            p = f"{overlay_dir}/{k:05d}.png"
            if os.path.exists(p):
                o = cv2.imread(p, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
                oa = o[..., 3:4]
                comp = comp * (1 - oa) + o[..., 2::-1] * oa

        frame = np.clip(comp * 255 + rng.random((H, W, 1), dtype=np.float32) - 0.5, 0, 255).astype(np.uint8)
        enc.stdin.write(frame.tobytes())
        if (k - k0) % 30 == 0:
            print(f"{k}/{k1}", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.kill()
    print("done", k0, k1, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:7])

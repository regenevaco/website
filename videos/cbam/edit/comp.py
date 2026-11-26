"""4K composite of one CBAM on-camera clip: keep the presenter and his chair, replace the room.

    python3 comp.py <cfg.json> <out.mp4> <k0> <k1>          encode output frames k0..k1-1
    python3 comp.py <cfg.json> <out_dir> --stills f1 f2 ...  PNG stills of source frames (QA)

cfg.json:
  video, matte (dir with alpha/ and landmarks.npy), plate_bg (chair-free clean plate, 16-bit PNG),
  chair_seen, chair_roi, reliable (masks from plate.py chair), studio (background PNG),
  segments: [[src_from, src_to], ...] kept source frames (no speed change),
  zoom: [z, ...] punch-in per segment, base_zoom, target: [x, y] (4K px) where the nose bridge goes.

Per frame:
  nose-mark repair, light skin / under-eye retouch -> 4K person matte (RVM, guided upsampling) refined in the
  edge band with the known clean background (alpha from colour distance to the background vs. the
  nearby solid foreground colour: fixes soft hair edges and motion-blurred hands) -> chair key (dark leather
  and teal piping inside the chair region) -> grade -> exact background replacement
  comp = clip(I - (1-a) B, 0, a) + (1-a) N  (B = old room, N = studio), so no old-wall colour, halo or
  patch survives at the edges -> light wrap -> fine grain -> framing (same face size in every clip, punch-ins)
  -> x264 BT.601 / tv range (matches the explainer).
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
Q = 4  # quarter-resolution helpers
TONEMAP = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv")
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)

_X = np.linspace(0, 1, 4096, dtype=np.float32)
_CURVE = np.clip(_X + 0.05 * np.sin(2 * np.pi * (_X - 0.5)) * _X * (1 - _X) * 2, 0, 1).astype(np.float32)


def grade(x):
    """Gentle grade shared by presenter and old background: slightly warmer, calmer saturation, soft S."""
    x = x * np.array([1.015, 1.0, 0.985], np.float32)
    lum = x @ LUMA
    x = lum[..., None] + (x - lum[..., None]) * np.float32(0.95)
    return _CURVE[(np.clip(x, 0, 1) * 4095).astype(np.int32)]


def smooth_landmarks(L, r=2):
    out = L.copy()
    for i in range(len(L)):
        w = L[max(0, i - r):i + r + 1]
        good = ~np.isnan(w[:, 0, 0])
        if good.any():
            out[i] = w[good].mean(0)
    miss = np.isnan(out[:, 0, 0])
    if miss.any():
        idx = np.where(~miss)[0]
        for i in np.where(miss)[0]:
            out[i] = out[idx[np.argmin(abs(idx - i))]]
    return out


def load16(path, size=None):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)[..., :3][..., ::-1]
    im = im.astype(np.float32) / (65535.0 if im.dtype == np.uint16 else 255.0)
    if size and (im.shape[1], im.shape[0]) != size:
        im = cv2.resize(im, size, interpolation=cv2.INTER_CUBIC)
    return np.ascontiguousarray(im)


def person_alpha(a1080, img, B, reliable):
    """RVM matte at 4K, refined inside the uncertain edge band with the known background."""
    a = cv2.resize(a1080, (W, H), interpolation=cv2.INTER_LINEAR)
    g = img @ LUMA
    a = np.clip(cv2.ximgproc.guidedFilter(g, a, 6, 1e-4), 0, 1)
    aq = cv2.resize(a, (W // Q, H // Q), interpolation=cv2.INTER_AREA)
    solid = cv2.erode((aq > 0.97).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
    band_q = (cv2.dilate((aq > 0.02).astype(np.uint8), np.ones((11, 11), np.uint8)) > 0) & (solid == 0)
    if not band_q.any():
        return a
    # nearby solid foreground colour (normalised convolution), quarter resolution
    iq = cv2.resize(img, (W // Q, H // Q), interpolation=cv2.INTER_AREA)
    den = cv2.GaussianBlur(solid, (0, 0), 5)
    Fq = cv2.GaussianBlur(iq * solid[..., None], (0, 0), 5) / (den[..., None] + 1e-6)
    den2 = cv2.GaussianBlur(solid, (0, 0), 16)
    Fq2 = cv2.GaussianBlur(iq * solid[..., None], (0, 0), 16) / (den2[..., None] + 1e-6)
    Fq = np.where((den > 0.05)[..., None], Fq, Fq2)
    near = np.clip((den - 0.03) / 0.10, 0, 1)            # a solid foreground colour is close by: F is trustworthy
    wq = cv2.GaussianBlur(band_q.astype(np.float32), (0, 0), 2) * band_q * near
    wb = cv2.resize(wq, (W, H), interpolation=cv2.INTER_LINEAR) * reliable
    ys, xs = np.where(wb > 0.01)
    F = cv2.resize(Fq, (W, H), interpolation=cv2.INTER_LINEAR)[ys, xs]
    Bb, Ib = B[ys, xs], img[ys, xs]
    d = F - Bb
    dd = (d * d).sum(1)
    akb = np.clip(((Ib - Bb) * d).sum(1) / np.maximum(dd, 1e-6), 0, 1)
    w = wb[ys, xs] * np.clip((dd - 0.008) / 0.01, 0, 1)   # trust only where fg and bg colours differ enough
    ar = a[ys, xs]
    ref = ar * (1 - w) + akb * w
    # bias against false foreground (old-room remnants): the refinement may remove alpha freely,
    # but may add at most what the network already saw
    a[ys, xs] = np.minimum(ref, 2.0 * ar)
    # background-difference cap: where the pixel still looks exactly like the old room, it is the old room
    # (sofa seen through a motion-blurred hand, wall between hair strands), whatever the network said
    ys, xs = np.where((a > 0.003) & (a < 0.985))
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    dsub = np.sqrt(((img[y0:y1, x0:x1] - B[y0:y1, x0:x1]) ** 2).sum(2))
    dsub = cv2.GaussianBlur(dsub, (0, 0), 1.5)
    diff = dsub[ys - y0, xs - x0]
    rel = reliable[ys, xs]
    cap = np.clip((diff - 0.02) / 0.12, 0, 1)
    cap = cap * cap * (3 - 2 * cap)                       # smoothstep: no hard 0/1 flicker near the threshold
    cap = cap * rel + (1 - rel)
    a[ys, xs] = np.minimum(a[ys, xs], cap)
    return a


def chair_alpha(img, core, roi_box, roi):
    # core here = chair leather seen in the clean plate (not the unseen area behind the presenter)
    """Chair kept as foreground: dark leather + teal piping inside the chair region, holes filled where the
    clean plate shows chair (so bright wall gaps between hair strands are never filled)."""
    y0, y1, x0, x1 = roi_box
    sub = img[y0:y1, x0:x1]
    hsv = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV)
    L = sub @ LUMA
    dark = np.clip((0.28 - L) / 0.06, 0, 1)
    teal = ((hsv[..., 0] > 168) & (hsv[..., 0] < 200) & (hsv[..., 1] > 0.45) & (hsv[..., 2] > 0.18)).astype(np.float32)
    m = np.maximum(dark, teal) * roi[y0:y1, x0:x1]
    hard = cv2.morphologyEx((m > 0.5).astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    # keep only dark/teal blobs connected to the chair itself (drops sofa buttons, seams, shadows)
    n, lab = cv2.connectedComponents(hard)
    ids = np.unique(lab[(hard > 0) & core[y0:y1, x0:x1]])
    hard = np.isin(lab, ids[ids > 0]).astype(np.uint8)
    m = m * cv2.dilate(hard, np.ones((5, 5), np.uint8))
    closed = cv2.morphologyEx(hard, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    fill = closed.copy()
    ff = np.zeros((fill.shape[0] + 2, fill.shape[1] + 2), np.uint8)
    cv2.floodFill(fill, ff, (0, 0), 1)
    holes = (fill == 0) & core[y0:y1, x0:x1]
    m = np.maximum(m, np.maximum(closed * core[y0:y1, x0:x1], holes).astype(np.float32))
    m = np.clip(cv2.ximgproc.guidedFilter(L, m, 3, 1e-3), 0, 1)
    out = np.zeros((H, W), np.float32)
    out[y0:y1, x0:x1] = m
    return out


def frame_gain(img, B, a, roi):
    """Exposure/white-balance drift of this frame vs. the plate, from clearly visible background."""
    s = slice(None, None, 8)
    m = (a[s, s] < 0.003) & (~roi[s, s])
    if m.sum() < 500:
        return np.ones(3, np.float32)
    r = img[s, s][m] / np.maximum(B[s, s][m], 0.02)
    return np.clip(np.median(r, 0), 0.85, 1.15).astype(np.float32)


class Clip:
    def __init__(self, cfg):
        self.cfg = cfg
        self.L = smooth_landmarks(np.load(f"{cfg['matte']}/landmarks.npy")[..., :2]) * 2.0
        self.B0 = load16(cfg["plate_bg"])
        self.N = load16(cfg["studio"], (W, H))
        self.core = cv2.dilate(cv2.imread(cfg["chair_seen"], 0), np.ones((9, 9), np.uint8)) > 0
        rel = (cv2.imread(cfg["reliable"], 0) > 0).astype(np.float32)
        self.reliable = cv2.GaussianBlur(cv2.erode(rel, np.ones((31, 31), np.uint8)), (0, 0), 12)
        roi = cv2.imread(cfg["chair_roi"], 0) > 0
        self.roi = roi
        ys, xs = np.where(roi)
        self.roi_box = (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)
        self.roif = roi.astype(np.float32)
        nq = cv2.resize(self.N, (W // Q, H // Q), interpolation=cv2.INTER_AREA)
        self.N_wrap = cv2.resize(cv2.GaussianBlur(nq, (0, 0), 10), (W, H), interpolation=cv2.INTER_LINEAR)

    def render(self, img, src, rng):
        lm = self.L[src]
        img = fix_scar(img, lm, 1.8, (1.4, 1.8), -0.06, 1.0)
        img = soften_skin(img, lm, 0.30)
        img = soften_under_eyes(img, lm, 0.45)
        a1080 = cv2.imread(f"{self.cfg['matte']}/alpha/{src:06d}.png", 0).astype(np.float32) / 255.0
        a0 = cv2.resize(a1080, (W, H), interpolation=cv2.INTER_LINEAR)
        B = self.B0 * frame_gain(img, self.B0, a0, self.roi)
        a = person_alpha(a1080, img, B, self.reliable)
        a = np.maximum(a, chair_alpha(img, self.core, self.roi_box, self.roif))
        img = tame_hair_shine(img, lm, a)
        img, Bg = grade(img), grade(B)
        a3 = a[..., None]
        fg = np.clip(img - (1 - a3) * Bg, 0, a3)
        fg *= np.clip((a3 - 0.015) / 0.06, 0, 1)          # pure background: drop old-room shadows and noise
        comp = fg + (1 - a3) * self.N
        aq = cv2.resize(a, (W // Q, H // Q), interpolation=cv2.INTER_AREA)
        inner = cv2.resize(cv2.GaussianBlur(aq, (0, 0), 4), (W, H), interpolation=cv2.INTER_LINEAR)
        wrap = (0.30 * a * np.clip(1 - inner, 0, 1))[..., None]
        comp = comp * (1 - wrap) + self.N_wrap * wrap
        n = cv2.resize(rng.standard_normal((H // 2, W // 2), dtype=np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        comp += (n * (0.0035 + 0.006 * (1 - a)))[..., None]
        return comp, a

    def frame_zoom(self, comp, seg, prog):
        cfg = self.cfg
        z = cfg["base_zoom"] * cfg["zoom"][seg] * (1 + 0.015 * prog)
        if z <= 1.0005:
            return comp
        cx, cy = self.seg_center[seg]
        tx, ty = cfg["target"]
        # place the nose bridge at the target, but never show beyond the frame
        x0 = float(np.clip(cx - tx / z, 0, W - W / z))
        y0 = float(np.clip(cy - ty / z, 0, H - H / z))
        M = np.array([[z, 0, -x0 * z], [0, z, -y0 * z]], np.float32)
        return cv2.warpAffine(comp, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def decode(video, frames):
    uniq = sorted(set(frames))
    ranges, s = [], uniq[0]
    for p, q in zip(uniq, uniq[1:] + [None]):
        if q is None or q != p + 1:
            ranges.append((s, p))
            s = q
    sel = "+".join(f"between(n\\,{a}\\,{b})" for a, b in ranges)
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", video, "-map", "0:v:0",
                            "-vf", f"fps={FPS},select='{sel}',{TONEMAP},format=gbrpf32le", "-fps_mode", "passthrough",
                            "-f", "rawvideo", "-pix_fmt", "gbrpf32le", "-"], stdout=subprocess.PIPE, bufsize=W * H * 12)
    fsz = W * H * 4
    for f in uniq:
        buf = dec.stdout.read(fsz * 3)
        if len(buf) < fsz * 3:
            break
        g, b, r = (np.frombuffer(buf[i * fsz:(i + 1) * fsz], np.float32).reshape(H, W) for i in range(3))
        yield f, np.ascontiguousarray(np.clip(np.stack([r, g, b], -1), 0, 1))
    dec.kill()


def main(cfg_path, out, *args):
    cfg = json.load(open(cfg_path))
    clip = Clip(cfg)
    segs = cfg["segments"]
    tl = [(f, si, (f - a) / max(1, b - a - 1)) for si, (a, b) in enumerate(segs) for f in range(a, b)]
    clip.seg_center = {si: np.nanmedian(clip.L[a:b, 6], axis=0) for si, (a, b) in enumerate(segs)}
    if args and args[0] == "--stills":
        os.makedirs(out, exist_ok=True)
        want = [int(x) for x in args[1:]]
        rng = np.random.default_rng(0)
        for f, img in decode(cfg["video"], want):
            comp, a = clip.render(img, f, rng)
            cv2.imwrite(f"{out}/c_{f:05d}.png", (np.clip(comp, 0, 1) * 65535).astype(np.uint16)[..., ::-1])
            cv2.imwrite(f"{out}/a_{f:05d}.png", (a * 255).astype(np.uint8))
            cv2.imwrite(f"{out}/s_{f:05d}.png", (img * 65535).astype(np.uint16)[..., ::-1])
            print("still", f, flush=True)
        return
    k0, k1 = int(args[0]), min(int(args[1]), len(tl))
    need = [tl[k][0] for k in range(k0, k1)]
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt601:out_range=tv",
         "-c:v", "libx264", "-preset", "medium", "-crf", "13", "-pix_fmt", "yuv420p",
         "-colorspace", "bt470bg", "-color_range", "tv", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(k0)
    frames = dict()
    gen = decode(cfg["video"], need)
    for k in range(k0, k1):
        src, si, prog = tl[k]
        while src not in frames:
            f, img = next(gen)
            frames = {f: img}
        comp, _ = clip.render(frames[src], src, rng)
        comp = clip.frame_zoom(comp, si, prog)
        frame = np.clip(comp * 255 + rng.random((H, W, 1), dtype=np.float32) - 0.5, 0, 255).astype(np.uint8)
        enc.stdin.write(frame.tobytes())
        if (k - k0) % 30 == 0:
            print(f"{k}/{k1}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("done", k0, k1, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

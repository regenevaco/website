"""Clean background plate for one on-camera clip, built from the clip's own background pixels.

    python3 plate.py <video.mov> <matte_dir> <out.png> [n_samples]
    python3 plate.py chair <plate.png> <plate_seen.png> <out_prefix>

For ~n_samples frames spread over the clip, the presenter (1080p RVM matte, upscaled and dilated)
is masked out; every background pixel takes the median of the frames where it was visible.
Pixels never visible (always behind the presenter) are inpainted; they are always covered by him,
so they only matter as a fallback. Output: 16-bit PNG, 3840x2160, BT.709 SDR (same tone map as the comp).
Also writes <out>_seen.png (255 where real pixels were seen).
"""
import os
import subprocess
import sys

import cv2
import numpy as np

W, H = 3840, 2160
TONEMAP = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv")


def main(video, mdir, out, n=28):
    n = int(n)
    na = len(os.listdir(f"{mdir}/alpha"))
    idx = np.linspace(5, na - 6, n).round().astype(int)
    sel = "+".join(f"eq(n\\,{i})" for i in idx)
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", video, "-map", "0:v:0",
                            "-vf", f"fps=30,select='{sel}',{TONEMAP},format=rgb48le", "-fps_mode", "passthrough",
                            "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"], stdout=subprocess.PIPE)
    stack = np.zeros((n, H, W, 3), np.uint16)
    valid = np.zeros((n, H, W), bool)
    k = np.ones((61, 61), np.uint8)
    for j, i in enumerate(idx):
        buf = dec.stdout.read(W * H * 6)
        stack[j] = np.frombuffer(buf, np.uint16).reshape(H, W, 3)
        a = cv2.imread(f"{mdir}/alpha/{i:06d}.png", 0)
        a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
        valid[j] = cv2.dilate((a > 4).astype(np.uint8), k) == 0
    dec.wait()
    plate = np.zeros((H, W, 3), np.uint16)
    seen = valid.any(0)
    for y0 in range(0, H, 120):
        s = stack[:, y0:y0 + 120].astype(np.float32)
        v = valid[:, y0:y0 + 120]
        s[~v] = np.nan
        with np.errstate(all="ignore"):
            m = np.nanmedian(s, axis=0)
        plate[y0:y0 + 120] = np.nan_to_num(m).astype(np.uint16)
    # fill never-seen pixels: inpaint at quarter resolution, upscale, paste only where unseen
    q = cv2.resize((plate >> 8).astype(np.uint8), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    hole = cv2.resize((~seen).astype(np.uint8) * 255, (W // 4, H // 4), interpolation=cv2.INTER_NEAREST)
    fill = cv2.inpaint(q, cv2.dilate(hole, np.ones((3, 3), np.uint8)), 9, cv2.INPAINT_TELEA)
    fill = cv2.resize(fill, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.uint16) * 257
    plate[~seen] = fill[~seen]
    cv2.imwrite(out, plate[..., ::-1])
    cv2.imwrite(out.replace(".png", "_seen.png"), seen.astype(np.uint8) * 255)
    print("seen", round(seen.mean(), 3))




def chair_masks(plate_png, seen_png, out_prefix):
    """From a plate: the chair's core (dark leather + teal piping, central blob), the chair ROI where a
    per-frame chair key is allowed, and a chair-free background (chair and unseen pixels inpainted)
    used to unmix edges. Writes <prefix>_core.png, <prefix>_roi.png, <prefix>_bg.png, plus <prefix>_chairseen.png
    (chair leather actually seen) and <prefix>_reliable.png (real room pixels, trusted for edge unmixing)."""
    p = cv2.imread(plate_png, -1)[..., ::-1].astype(np.float32) / 65535.0
    seen = cv2.imread(seen_png, 0) > 0
    hsv = cv2.cvtColor(p, cv2.COLOR_RGB2HSV)
    L = p @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    dark = L < 0.30
    teal = (hsv[..., 0] > 160) & (hsv[..., 0] < 205) & (hsv[..., 1] > 0.3) & (hsv[..., 2] > 0.2)
    m = ((dark | teal) & seen) | ~seen
    m[:, :int(0.28 * W)] = False
    m[:, int(0.72 * W):] = False
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.004 * W * H]
    core = np.isin(lab, keep)
    top = np.where(core.any(1))[0].min()
    roi = cv2.dilate(core.astype(np.uint8), np.ones((161, 161), np.uint8)) > 0
    roi[:max(0, top - 120)] = False
    seen_chair = core & seen & (dark | teal)
    reliable = seen & ~(cv2.dilate(seen_chair.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0)
    cv2.imwrite(out_prefix + "_core.png", core.astype(np.uint8) * 255)
    cv2.imwrite(out_prefix + "_chairseen.png", seen_chair.astype(np.uint8) * 255)
    cv2.imwrite(out_prefix + "_reliable.png", reliable.astype(np.uint8) * 255)
    cv2.imwrite(out_prefix + "_roi.png", roi.astype(np.uint8) * 255)
    # chair-free background: inpaint chair + unseen at quarter resolution, keep real wall/sofa elsewhere
    seen_chair0 = core & seen & (dark | teal)
    hole = (cv2.dilate(seen_chair0.astype(np.uint8), np.ones((81, 81), np.uint8)) |
            cv2.dilate((~seen).astype(np.uint8), np.ones((15, 15), np.uint8)))
    q = cv2.resize(p, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    known = (cv2.resize(hole, (W // 4, H // 4), interpolation=cv2.INTER_NEAREST) == 0).astype(np.float32)
    # smooth normalized-convolution fill (the wall and sofa are smooth), fine scale first, coarse where sparse
    fill = np.zeros_like(q)
    weight = np.zeros(q.shape[:2], np.float32)
    for sig in (6, 18, 60, 200, 600):
        den = cv2.GaussianBlur(known, (0, 0), sig)
        num = cv2.GaussianBlur(q * known[..., None], (0, 0), sig)
        est = num / (den[..., None] + 1e-6)
        take = (np.clip((den - 0.05) / 0.25, 0, 1) if sig < 600 else (den > 1e-4).astype(np.float32)) * (1 - weight)
        fill += est * take[..., None]
        weight += take
    fill = fill / np.maximum(weight, 1e-6)[..., None]
    fill = cv2.resize(fill, (W, H), interpolation=cv2.INTER_CUBIC)
    bg = np.where(hole[..., None] > 0, fill, p)
    cv2.imwrite(out_prefix + "_bg.png", (np.clip(bg, 0, 1) * 65535).astype(np.uint16)[..., ::-1])
    print("chair top", top, "core", round(core.mean(), 3), "roi", round(roi.mean(), 3))


if __name__ == "__main__":
    if sys.argv[1] == "chair":
        chair_masks(*sys.argv[2:5])
    else:
        main(*sys.argv[1:5])

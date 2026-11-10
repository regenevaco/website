"""Natural-looking face retouch driven by MediaPipe face-mesh landmarks (478 points, in frame pixels).

fix_scar(img, lm)   removes the small scar on the upper nose bridge. Only the darker, browner
                    blotch is lifted back to the surrounding skin tone (low-frequency, positive
                    correction only), so pores, fine texture and the natural ridge highlight remain.
soften_skin(img, lm, amount)  light frequency-separation retouch on the cheeks/forehead/nose:
                    mid-frequency blotchiness is reduced a little, pore-level texture is kept.
                    Eyes, brows, lips, beard line and hair are excluded.
img: float32 RGB in [0, 1] (any size); lm: (478, 2) landmarks in the same pixel space.
"""
import cv2
import numpy as np

# Face-mesh landmark indices
BROW_MID, BRIDGE = 168, 6
EYE_R_IN, EYE_L_IN = 133, 362
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152,
             148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
EYE_R = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
EYE_L = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
BROW_R = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
BROW_L = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
NOSTRILS = [98, 97, 2, 326, 327, 294, 278, 344, 440, 275, 4, 45, 220, 115, 48, 64]


def _frame(lm):
    a, b = lm[EYE_R_IN], lm[EYE_L_IN]
    iod = float(np.linalg.norm(b - a))
    u = (b - a) / max(iod, 1e-6)          # across the face (viewer left -> right)
    v = np.array([-u[1], u[0]])           # down the face
    return iod, u, v


def scar_geometry(lm):
    """Centre and radii of the scar region, from the brow-mid and bridge landmarks."""
    iod, u, v = _frame(lm)
    c = lm[BROW_MID] + 0.7 * (lm[BRIDGE] - lm[BROW_MID]) - 0.06 * iod * u
    return c, 0.17 * iod, 0.12 * iod, u, iod


def fix_scar(img, lm, strength=1.0):
    c, rx, ry, u, iod = scar_geometry(lm)
    r = int(max(rx, ry) * 3.2) + 8
    x0, y0 = int(c[0]) - r, int(c[1]) - r
    x1, y1 = x0 + 2 * r, y0 + 2 * r
    H, W = img.shape[:2]
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
        return img
    roi = img[y0:y1, x0:x1].astype(np.float32)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - c[0], yy - c[1]
    pu = dx * u[0] + dy * u[1]
    pv = -dx * u[1] + dy * u[0]
    d = (pu / rx) ** 2 + (pv / ry) ** 2
    soft = np.clip(1.45 - d * 0.9, 0, 1)                    # feathered ellipse (full inside, fades out by d~1.6)
    soft = cv2.GaussianBlur(soft, (0, 0), max(1.0, 0.03 * iod))
    hole = (d < 1.6).astype(np.float32)                     # excluded from the clean estimate

    s_lf = max(1.2, 0.018 * iod)                            # blotch scale
    lf = cv2.GaussianBlur(roi, (0, 0), s_lf)
    s_fill = max(4.0, 0.09 * iod)
    w = 1.0 - hole
    num = cv2.GaussianBlur(lf * w[..., None], (0, 0), s_fill)
    den = cv2.GaussianBlur(w, (0, 0), s_fill)[..., None] + 1e-6
    clean = num / den                                       # skin tone interpolated from around the scar
    lift = np.clip(clean - lf, 0, None)                     # only brighten what is darker than its surroundings
    hf = roi - lf
    dark_detail = np.clip(hf, None, 0)                      # the scar's dark fine edges (highlights untouched)
    out = roi + strength * soft[..., None] * (lift - 0.75 * dark_detail)
    res = img.copy()
    res[y0:y1, x0:x1] = out
    return res


def _poly_mask(shape, pts, blur):
    m = np.zeros(shape, np.float32)
    cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1.0)
    return cv2.GaussianBlur(m, (0, 0), blur) if blur > 0 else m


def soften_skin(img, lm, amount=0.35):
    iod, _, _ = _frame(lm)
    xs, ys = lm[FACE_OVAL, 0], lm[FACE_OVAL, 1]
    pad = int(0.3 * iod)
    x0, y0 = max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad)
    x1, y1 = min(img.shape[1], int(xs.max()) + pad), min(img.shape[0], int(ys.max()) + pad)
    roi = img[y0:y1, x0:x1]
    off = np.array([x0, y0], np.float32)
    shp = roi.shape[:2]
    f = 0.04 * iod
    m = _poly_mask(shp, lm[FACE_OVAL] - off, f)
    for part, grow in ((EYE_R, 1.6), (EYE_L, 1.6), (BROW_R, 1.4), (BROW_L, 1.4), (LIPS, 1.25), (NOSTRILS, 1.0)):
        p = lm[part] - off
        cen = p.mean(0)
        m *= 1.0 - _poly_mask(shp, cen + (p - cen) * grow, f)
    # Keep beard/stubble out: only smooth pixels that look like skin (not dark hair).
    lum = roi @ np.array([0.299, 0.587, 0.114], np.float32)
    skin = np.clip((lum - 0.18) / 0.12, 0, 1)
    m *= cv2.GaussianBlur(skin, (0, 0), 0.01 * iod + 1)
    # Frequency separation: fine (<s1) texture kept, blotches between s1 and s2 reduced.
    s1, s2 = max(1.0, 0.012 * iod), max(4.0, 0.07 * iod)
    b1 = cv2.GaussianBlur(roi, (0, 0), s1)
    b2 = cv2.GaussianBlur(roi, (0, 0), s2)
    mid = b1 - b2
    out = roi - amount * m[..., None] * mid
    res = img.copy()
    res[y0:y1, x0:x1] = out
    return res


LID_R = [33, 7, 163, 144, 145, 153, 154, 155, 133]
LID_L = [362, 382, 381, 380, 374, 373, 390, 249, 263]


def soften_under_eyes(img, lm, amount=0.55):
    """Reduce dark circles: lift the under-eye area part of the way toward the surrounding cheek tone."""
    iod, u, v = _frame(lm)
    res = img
    for lid in (LID_R, LID_L):
        p = lm[lid]
        low = p + v * 0.38 * iod
        poly = np.vstack([p + v * 0.03 * iod, low[::-1]])
        x0, y0 = (poly.min(0) - 0.5 * iod).astype(int)
        x1, y1 = (poly.max(0) + 0.5 * iod).astype(int)
        if x0 < 0 or y0 < 0 or x1 > img.shape[1] or y1 > img.shape[0]:
            continue
        roi = res[y0:y1, x0:x1]
        shp = roi.shape[:2]
        m = _poly_mask(shp, poly - [x0, y0], 0.05 * iod)
        hole = _poly_mask(shp, poly - [x0, y0], 0) 
        hole = cv2.dilate(hole, np.ones((3, 3), np.uint8), iterations=max(1, int(0.03 * iod)))
        lf = cv2.GaussianBlur(roi, (0, 0), max(2.0, 0.03 * iod))
        w = 1.0 - hole
        s = max(6.0, 0.2 * iod)
        clean = cv2.GaussianBlur(lf * w[..., None], (0, 0), s) / (cv2.GaussianBlur(w, (0, 0), s)[..., None] + 1e-6)
        lift = np.clip(clean - lf, 0, None)
        if res is img:
            res = img.copy()
        res[y0:y1, x0:x1] = roi + amount * m[..., None] * lift
    return res


def tame_hair_shine(img, lm, alpha, amount=0.8):
    """Soften the bright specular patches on the hair (overhead-light shine) toward the hair's own tone."""
    iod, _, _ = _frame(lm)
    ov = lm[FACE_OVAL]
    brow_y = lm[BROW_R + BROW_L, 1].min()
    x0, x1 = int(ov[:, 0].min() - 0.8 * iod), int(ov[:, 0].max() + 0.8 * iod)
    y0, y1 = int(ov[:, 1].min() - 2.4 * iod), int(brow_y)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.shape[1], x1), min(img.shape[0], y1)
    if x1 - x0 < 10 or y1 - y0 < 10:
        return img
    roi = img[y0:y1, x0:x1]
    a = alpha[y0:y1, x0:x1]
    shp = roi.shape[:2]
    face = _poly_mask(shp, ov - [x0, y0], 0.03 * iod)
    hair = np.clip(a * 1.2 - 0.2, 0, 1) * (1 - np.clip(face * 1.5, 0, 1))
    lum = roi @ np.array([0.299, 0.587, 0.114], np.float32)
    k = max(3, int(0.14 * iod)) | 1
    base = cv2.GaussianBlur(cv2.erode(roi, np.ones((k, k), np.uint8)), (0, 0), 0.05 * iod)
    blum = base @ np.array([0.299, 0.587, 0.114], np.float32)
    sat = roi.max(-1) - roi.min(-1)
    h = np.clip((lum - blum - 0.03) / 0.16, 0, 1) * np.clip(1 - sat / 0.25, 0, 1) * hair
    h = cv2.GaussianBlur(h, (0, 0), 0.01 * iod + 0.5)
    res = img.copy()
    res[y0:y1, x0:x1] = roi + amount * h[..., None] * (base - roi)
    return res

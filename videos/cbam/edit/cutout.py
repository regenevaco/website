"""Thumbnail cutout from a portrait photo: same nose-mark repair and light retouch as the video, then a
clean RGBA cutout (RVM matte, guided-filter refined against the plain wall, wall colour unmixed from the edges).

    python3 -I cutout.py <photo.jpg> <out.png> <models_dir>
"""
import os
import sys

import cv2
import mediapipe as mp
import numpy as np
import onnxruntime as ort

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retouch import fix_scar, soften_skin, soften_under_eyes  # noqa: E402


def main(photo, out, models):
    bgr = cv2.imread(photo, cv2.IMREAD_COLOR)                 # applies EXIF orientation
    img = bgr[..., ::-1].astype(np.float32) / 255.0
    H, W = img.shape[:2]

    det = mp.tasks.vision.FaceLandmarker.create_from_options(mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=f"{models}/face_landmarker.task"), num_faces=1))
    res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(bgr[..., ::-1])))
    if res.face_landmarks:
        lm = np.array([[p.x * W, p.y * H] for p in res.face_landmarks[0]], np.float32)
        img = fix_scar(img, lm, 1.0, (1.6, 2.1), -0.08, 1.0)        # stills: gentler, wider than the video setting
        img = soften_skin(img, lm, 0.30)
        img = soften_under_eyes(img, lm, 0.45)
    else:
        print("no face found: retouch skipped")

    # work at <= 2200 px tall (plenty for a 2560x1440 thumbnail)
    sc = min(1.0, 2200 / H)
    if sc < 1:
        img = cv2.resize(img, (int(W * sc), int(H * sc)), interpolation=cv2.INTER_AREA)
        H, W = img.shape[:2]
    so = ort.SessionOptions()
    so.intra_op_num_threads = 2
    rvm = ort.InferenceSession(f"{models}/rvm_resnet50_fp32.onnx", so, providers=["CPUExecutionProvider"])
    rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
    src = img.transpose(2, 0, 1)[None].astype(np.float32)
    dsr = np.array([min(1.0, 640 / max(H, W))], np.float32)
    for _ in range(3):                                         # let the recurrent state settle on the still
        _, pha, *rec = rvm.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                      "downsample_ratio": dsr})
    a = np.clip(pha[0, 0], 0, 1).astype(np.float32)
    a = np.clip(cv2.ximgproc.guidedFilter(img @ np.array([0.299, 0.587, 0.114], np.float32), a, 6, 1e-4), 0, 1)
    # unmix the wall colour out of soft edges (estimated from nearby clear background)
    q = 4
    aq = cv2.resize(a, (W // q, H // q), interpolation=cv2.INTER_AREA)
    bgw = (cv2.dilate((aq > 0.02).astype(np.uint8), np.ones((5, 5), np.uint8)) == 0).astype(np.float32)
    iq = cv2.resize(img, (W // q, H // q), interpolation=cv2.INTER_AREA)
    B = cv2.GaussianBlur(iq * bgw[..., None], (0, 0), 12) / (cv2.GaussianBlur(bgw, (0, 0), 12)[..., None] + 1e-4)
    B = cv2.resize(B, (W, H), interpolation=cv2.INTER_LINEAR)
    # refine soft edges against the plain wall: pixels that look exactly like the wall are wall
    diff = np.sqrt(((img - B) ** 2).sum(2))
    cap = np.clip((cv2.GaussianBlur(diff, (0, 0), 1.2) - 0.03) / 0.12, 0, 1)
    a = np.where((a > 0) & (a < 0.985), np.minimum(a, cap * cap * (3 - 2 * cap)), a)
    a[a < 0.02] = 0
    edge = (a > 0) & (a < 1)
    F = img.copy()
    F[edge] = np.clip((img[edge] - (1 - a[edge])[..., None] * B[edge]) / np.maximum(a[edge], 0.2)[..., None], 0, 1)

    rgba = np.dstack([F[..., ::-1], a])
    cv2.imwrite(out, (rgba * 255 + 0.5).astype(np.uint8))
    print(out, W, H)


if __name__ == "__main__":
    main(*sys.argv[1:4])

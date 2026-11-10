"""Stage 1: alpha matte (Robust Video Matting) + face landmarks for every frame.

    python3 matte.py <video.mov> <out_dir> <models_dir>

Decodes the iPhone HLG clip, tone-maps it to SDR BT.709 at 1920x1080, and writes:
  out_dir/alpha/000000.png   8-bit matte per frame (1080p; upscaled to 4K later)
  out_dir/landmarks.npy      (frames, 478, 3) face-mesh points in 1080p pixels, NaN if no face
"""
import os
import subprocess
import sys

import cv2
import mediapipe as mp
import numpy as np
import onnxruntime as ort

W, H = 1920, 1080
TONEMAP = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def frames(path, w, h):
    cmd = ["ffmpeg", "-loglevel", "error", "-i", path, "-map", "0:v:0",
           "-vf", f"{TONEMAP},fps=30,scale={w}:{h}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=w * h * 3 * 4)
    n = w * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


def main(video, out, models):
    os.makedirs(f"{out}/alpha", exist_ok=True)
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    rvm = ort.InferenceSession(f"{models}/rvm_resnet50_fp32.onnx", so, providers=["CPUExecutionProvider"])
    rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
    dsr = np.array([0.25], np.float32)

    opts = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=f"{models}/face_landmarker.task"),
        running_mode=mp.tasks.vision.RunningMode.VIDEO, num_faces=1)
    lm_det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

    lms = []
    for i, img in enumerate(frames(video, W, H)):
        src = img.astype(np.float32).transpose(2, 0, 1)[None] / 255.0
        fgr, pha, *rec = rvm.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                       "downsample_ratio": dsr})
        a = (np.clip(pha[0, 0], 0, 1) * 255 + 0.5).astype(np.uint8)
        cv2.imwrite(f"{out}/alpha/{i:06d}.png", a)

        res = lm_det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img)),
                                      int(i * 1000 / 30))
        if res.face_landmarks:
            lms.append([[p.x * W, p.y * H, p.z * W] for p in res.face_landmarks[0]])
        else:
            lms.append([[np.nan] * 3] * 478)
        if i % 60 == 0:
            print(i, flush=True)
            np.save(f"{out}/landmarks.npy", np.array(lms, np.float32))
    np.save(f"{out}/landmarks.npy", np.array(lms, np.float32))
    print("done", len(lms), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])

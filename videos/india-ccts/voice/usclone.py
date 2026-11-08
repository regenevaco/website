"""Surya US Accent Clone: US-accented speech, converted to Surya's voice.

Pipeline
  1. Kokoro (US English voice) speaks the text with a native US accent and prosody.
  2. kNN-VC (WavLM-Large features + pre-matched HiFi-GAN, MIT licence) replaces every
     ~20 ms frame with its nearest neighbours from Surya's own recording, so the
     timbre becomes Surya's while the US pronunciation and rhythm are kept.

    python3 usclone.py "<text>" out.wav [kokoro_voice]

Environment:
    KNNVC_DIR          folder with the kNN-VC repo files (matcher.py, wavlm/, hifigan/)
    KNNVC_WEIGHTS      folder with WavLM-Large.pt and prematch_g_02500000.pt
    KOKORO_DIR         folder with kokoro-v1.0.onnx and voices-v1.0.bin
    SURYA_MATCH_WAV    Surya's long polished recording (outside the repo)
    SURYA_MATCH_CACHE  optional .pt cache of its WavLM features
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.environ["KNNVC_DIR"])
import torch  # noqa: E402
import torchaudio  # noqa: E402
from hifigan.models import Generator as HiFiGAN  # noqa: E402
from hifigan.utils import AttrDict  # noqa: E402
from matcher import KNeighborsVC  # noqa: E402
from wavlm.WavLM import WavLM, WavLMConfig  # noqa: E402

torch.set_num_threads(4)


def load_knnvc():
    root, w = os.environ["KNNVC_DIR"], os.environ["KNNVC_WEIGHTS"]
    h = AttrDict(json.load(open(os.path.join(root, "hifigan", "config_v1_wavlm.json"))))
    gen = HiFiGAN(h)
    gen.load_state_dict(torch.load(os.path.join(w, "prematch_g_02500000.pt"), map_location="cpu")["generator"])
    gen.eval()
    gen.remove_weight_norm()
    ck = torch.load(os.path.join(w, "WavLM-Large.pt"), map_location="cpu")
    wavlm = WavLM(WavLMConfig(ck["cfg"]))
    wavlm.load_state_dict(ck["model"])
    wavlm.eval()
    return KNeighborsVC(wavlm, gen, h, "cpu")


class USClone:
    def __init__(self, voice="am_michael", speed=1.0):
        from kokoro_onnx import Kokoro
        kd = os.environ["KOKORO_DIR"]
        self.tts = Kokoro(os.path.join(kd, "kokoro-v1.0.onnx"), os.path.join(kd, "voices-v1.0.bin"))
        self.voice, self.speed = voice, speed
        self.vc = load_knnvc()
        cache = os.environ.get("SURYA_MATCH_CACHE")
        if cache and os.path.exists(cache):
            self.match_set = torch.load(cache)
        else:
            x, sr = torchaudio.load(os.environ["SURYA_MATCH_WAV"])
            x = torchaudio.functional.resample(x.mean(0, keepdim=True), sr, 16000)
            feats = [self.vc.get_features(x[:, i:i + 16000 * 30]) for i in range(0, x.shape[1], 16000 * 30)]
            self.match_set = torch.cat(feats, 0)
            if cache:
                torch.save(self.match_set, cache)

    def say(self, text, topk=4):
        a, sr = self.tts.create(text, voice=self.voice, speed=self.speed, lang="en-us")
        x = torchaudio.functional.resample(torch.tensor(a, dtype=torch.float32)[None], sr, 16000)
        q = self.vc.get_features(x)
        out = self.vc.match(q, self.match_set, topk=topk)
        return out.numpy().astype(np.float32), 16000


if __name__ == "__main__":
    c = USClone(sys.argv[3] if len(sys.argv) > 3 else "am_michael")
    w, sr = c.say(sys.argv[1])
    sf.write(sys.argv[2], w, sr)

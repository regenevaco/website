"""Zero-shot voice cloning with ZipVoice ONNX models, run directly (no sherpa tokenizer).

Pipeline (mirrors k2-fsa/ZipVoice onnx_infer.py):
  espeak IPA tokens -> text encoder -> flow-matching decoder (Euler, CFG) -> Vocos ISTFT.
"""
import os
import re
import numpy as np
import onnxruntime as ort
import soundfile as sf
import espeakng_loader
from phonemizer.backend.espeak.wrapper import EspeakWrapper
from phonemizer import phonemize
from phonemizer.separator import Separator

EspeakWrapper.set_library(espeakng_loader.get_library_path())
EspeakWrapper.set_data_path(espeakng_loader.get_data_path())

SR, NFFT, HOP, NMELS = 24000, 1024, 256, 100
FEAT_SCALE, TARGET_RMS = 0.1, 0.1


def mel_fbank():
    # torchaudio.functional.melscale_fbanks(htk, norm=None)
    n_freqs = NFFT // 2 + 1
    all_freqs = np.linspace(0, SR / 2, n_freqs)
    m_min, m_max = 2595 * np.log10(1 + 0 / 700), 2595 * np.log10(1 + (SR / 2) / 700)
    m_pts = np.linspace(m_min, m_max, NMELS + 2)
    f_pts = 700 * (10 ** (m_pts / 2595) - 1)
    f_diff = f_pts[1:] - f_pts[:-1]
    slopes = f_pts[None, :] - all_freqs[:, None]
    down = -slopes[:, :-2] / f_diff[:-1]
    up = slopes[:, 2:] / f_diff[1:]
    return np.maximum(0, np.minimum(down, up))  # (n_freqs, n_mels)


WIN = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(NFFT) / NFFT)).astype(np.float32)  # periodic hann
FB = mel_fbank().astype(np.float32)


def fbank(wav):
    x = np.pad(wav, (NFFT // 2, NFFT // 2), mode="reflect")
    n = 1 + (len(x) - NFFT) // HOP
    frames = np.stack([x[i * HOP: i * HOP + NFFT] * WIN for i in range(n)])
    mag = np.abs(np.fft.rfft(frames, axis=1))  # power=1
    mel = mag @ FB
    return np.log(np.clip(mel, 1e-7, None)).astype(np.float32)  # (T, 100)


def istft(mag, cos, sin):
    spec = mag * (cos + 1j * sin)  # (F, T)
    frames = np.fft.irfft(spec.T, n=NFFT, axis=1) * WIN
    n = frames.shape[0]
    out = np.zeros(NFFT + HOP * (n - 1), dtype=np.float64)
    norm = np.zeros_like(out)
    for i in range(n):
        out[i * HOP: i * HOP + NFFT] += frames[i]
        norm[i * HOP: i * HOP + NFFT] += WIN ** 2
    out = out / np.maximum(norm, 1e-8)
    return out[NFFT // 2: -NFFT // 2].astype(np.float32)


class ZipClone:
    def __init__(self, model_dir, vocoder, tokens, ref_wav, ref_text, threads=4,
                 encoder="text_encoder.onnx", decoder="fm_decoder.onnx"):
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        p = ["CPUExecutionProvider"]
        self.enc = ort.InferenceSession(os.path.join(model_dir, encoder), so, providers=p)
        self.dec = ort.InferenceSession(os.path.join(model_dir, decoder), so, providers=p)
        self.voc = ort.InferenceSession(vocoder, so, providers=p)
        self.tok = {}
        for line in open(tokens, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 2:
                self.tok[parts[0]] = int(parts[1])
        self.prompts = {}
        self.add_prompt("default", ref_wav, ref_text)

    def add_prompt(self, name, ref_wav, ref_text):
        """Register a reference clip (24 kHz mono) and its exact transcript as a delivery style."""
        wav, sr = sf.read(ref_wav, dtype="float32")
        assert sr == SR, "reference must be 24 kHz mono"
        rms = float(np.sqrt(np.mean(wav ** 2)))
        if rms < TARGET_RMS:
            wav = wav * TARGET_RMS / rms
        self.prompts[name] = (fbank(wav)[None] * FEAT_SCALE, self.tokens(ref_text), rms)

    def ipa(self, text):
        return phonemize(text, language="en-us", backend="espeak", strip=True, with_stress=True,
                         preserve_punctuation=True, punctuation_marks=';:,.!?',
                         separator=Separator(phone="", word=" "), njobs=1)

    def tokens(self, text):
        # [[...]] passes raw IPA through, for names espeak gets wrong (e.g. [[sˈuːɹjə]]).
        parts = re.split(r"\[\[(.*?)\]\]", text)
        ipa = " ".join((p if i % 2 else self.ipa(p)).strip() for i, p in enumerate(parts) if p.strip())
        ids = [self.tok[c] for c in ipa if c in self.tok]
        return np.array([ids], dtype=np.int64)

    def say(self, text, speed=1.0, steps=8, guidance=3.0, t_shift=0.5, seed=0, prompt="default"):
        prompt_feat, prompt_tokens, prompt_rms = self.prompts[prompt]
        tokens = self.tokens(text)
        cond = self.enc.run(None, {"tokens": tokens, "prompt_tokens": prompt_tokens,
                                   "prompt_features_len": np.array(prompt_feat.shape[1], dtype=np.int64),
                                   "speed": np.array(speed, dtype=np.float32)})[0]
        n, frames, dim = cond.shape
        plen = prompt_feat.shape[1]
        speech_cond = np.zeros((n, frames, dim), dtype=np.float32)
        speech_cond[:, :plen] = prompt_feat
        ts = np.linspace(0, 1, steps + 1)
        ts = t_shift * ts / (1 + (t_shift - 1) * ts)
        rng = np.random.default_rng(seed)
        x = rng.standard_normal((n, frames, dim)).astype(np.float32)
        for i in range(steps):
            v = self.dec.run(None, {"t": np.array(ts[i], dtype=np.float32), "x": x, "text_condition": cond,
                                    "speech_condition": speech_cond,
                                    "guidance_scale": np.array(guidance, dtype=np.float32)})[0]
            x = x + v * np.float32(ts[i + 1] - ts[i])
        feat = x[:, plen:, :] / FEAT_SCALE  # (1, T, 100)
        mag, cos, sin = self.voc.run(None, {"mels": feat.transpose(0, 2, 1).astype(np.float32)})
        wav = istft(mag[0], cos[0], sin[0])
        if prompt_rms < TARGET_RMS:
            wav = wav * prompt_rms / TARGET_RMS
        return wav

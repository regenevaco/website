#!/usr/bin/env bash
# One-time setup for the Surya voice clone kit (Linux or macOS, Python 3.10+).
# Installs Python packages and downloads the open-source models (~1.5 GB) into ./models.
set -euo pipefail
cd "$(dirname "$0")"
pip install -q onnxruntime sherpa-onnx espeakng-loader phonemizer soundfile scipy numpy
command -v ffmpeg >/dev/null || { echo "Please install ffmpeg (apt-get install ffmpeg / brew install ffmpeg)"; exit 1; }
mkdir -p models && cd models
R=https://github.com/k2-fsa/sherpa-onnx/releases/download
get() { [ -e "$2" ] || { echo "downloading $2"; curl -sSL --retry 3 "$1" -o "$2.tmp" && mv "$2.tmp" "$2"; }; }
get $R/tts-models/sherpa-onnx-zipvoice-zh-en-emilia.tar.bz2 zipvoice.tar.bz2
get $R/tts-models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2 zipvoice-tokens.tar.bz2
get $R/vocoder-models/vocos_24khz.onnx vocos_24khz.onnx
get $R/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2 parakeet.tar.bz2
get $R/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx wespeaker_en_voxceleb_resnet34_LM.onnx
for t in zipvoice zipvoice-tokens parakeet; do [ -f "$t.done" ] || { tar xjf "$t.tar.bz2" && rm "$t.tar.bz2" && touch "$t.done"; }; done
echo "Setup complete."

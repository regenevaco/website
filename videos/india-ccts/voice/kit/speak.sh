#!/usr/bin/env bash
# Usage: ./speak.sh "Text to say" output_name [style ...]
#   styles: explanatory (clearest), warm, emphatic, curious   (default: warm emphatic -> best take kept)
# Writes output_name.wav (48 kHz, 24-bit), output_name.mp3 (320 kbps) and output_name.json (quality scores).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export SURYA_VOICE_MODELS="$HERE/models" SURYA_VOICE_REF_DIR="$HERE/refs"
TEXT="$1"; OUT="$2"; shift 2
python3 "$HERE/say_line.py" "$TEXT" "${SAY:-$TEXT}" "$OUT" "$@"

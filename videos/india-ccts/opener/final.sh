#!/usr/bin/env bash
# Join the composited opener to the explainer and encode the 4K delivery file.
#   ./final.sh <work_dir> <explainer_video.mp4> <explainer_mix.wav> <out.mp4> [video_kbps]
# work_dir: chunks/c_*.mp4 (opener video), opener_mix.wav (opener audio).
# The explainer slides in over the last 0.6 s of the opener; its audio is layered (not cross-faded)
# so the presenter's last word is never faded out, with a soft whoosh on the transition.
set -euo pipefail
W="$1"; EXPL="$2"; EMIX="$3"; OUT="$4"; VK="${5:-2880}"
XF=0.6

ls "$W"/chunks/c_*.mp4 | sort -t_ -k2 -n | sed "s/^/file '/; s/$/'/" > "$W/chunks/list.txt"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$W/chunks/list.txt" -c copy "$W/opener_4k.mp4"
N=$(ffprobe -v error -count_packets -select_streams v -show_entries stream=nb_read_packets -of csv=p=0 "$W/opener_4k.mp4")
OFF=$(python3 -c "print(round($N/30 - $XF, 3))")
echo "opener frames $N, explainer starts at $OFF s"

python3 - "$W/whoosh.wav" <<'EOF'
import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt
sr, d = 48000, 0.9
n = int(sr * d); t = np.arange(n) / sr
x = np.random.default_rng(3).standard_normal(n)
out = np.zeros(n)
for i in range(0, n, 480):                      # band-pass sweep 400 Hz -> 5 kHz
    f = 400 * (5000 / 400) ** (i / n)
    sos = butter(2, [f * 0.7, min(f * 1.4, 23000)], "band", fs=sr, output="sos")
    out[i:i + 480] = sosfilt(sos, x[max(0, i - 2000):i + 480])[-len(out[i:i + 480]):]
env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
y = out * env; y /= np.abs(y).max() + 1e-9
sf.write(sys.argv[1], np.stack([y, y], 1).astype(np.float32) * 0.5, sr)
EOF

DMS=$(python3 -c "print(int(round($OFF*1000)))")
WMS=$(python3 -c "print(int(round(($OFF-0.35)*1000)))")
FC="[0:v]fps=30,settb=AVTB,setpts=PTS-STARTPTS,setsar=1[o];[1:v]fps=30,settb=AVTB,setpts=PTS-STARTPTS,setsar=1[x];\
[o][x]xfade=transition=smoothleft:duration=$XF:offset=$OFF,format=yuv420p[v];\
[3:a]adelay=$DMS|$DMS[e];[4:a]adelay=$WMS|$WMS,volume=0.22[w];\
[2:a][e][w]amix=inputs=3:normalize=0:duration=longest,alimiter=limit=0.89[a]"
COMMON=(-i "$W/opener_4k.mp4" -i "$EXPL" -i "$W/opener_mix.wav" -i "$EMIX" -i "$W/whoosh.wav" -filter_complex "$FC")
ENC=(-c:v libx264 -preset medium -b:v "${VK}k" -maxrate 5500k -bufsize 11000k -profile:v high -pix_fmt yuv420p -g 60
     -colorspace bt470bg -color_range tv)
cd "$W"
ffmpeg -y -loglevel error -stats "${COMMON[@]}" -map "[v]" "${ENC[@]}" -pass 1 -passlogfile "$W/x264f" -an -f null /dev/null
ffmpeg -y -loglevel error -stats "${COMMON[@]}" -map "[v]" -map "[a]" "${ENC[@]}" -pass 2 -passlogfile "$W/x264f" \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$OUT"
rm -f "$W"/x264f*
ffprobe -v error -count_packets -show_entries stream=codec_name,width,height,nb_read_packets -show_entries format=duration,size -of compact "$OUT"

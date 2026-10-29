#!/usr/bin/env bash
# Mix narration + music + whooshes, normalize to YouTube loudness (-14 LUFS)
# and mux with the rendered silent video.
#   ./mix.sh <build_dir> <silent.mp4> <out.mp4>
set -euo pipefail
B="$1"; V="$2"; OUT="$3"

ffmpeg -y -loglevel error \
  -i "$B/narration.wav" -i "$B/music.wav" -i "$B/sfx.wav" \
  -filter_complex "
    [0:a]aresample=48000,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,
         equalizer=f=3500:t=q:w=1.2:g=2,pan=stereo|c0=c0|c1=c0,asplit=2[voice][key];
    [1:a]volume=0.075[m];
    [m][key]sidechaincompress=threshold=0.05:ratio=3:attack=60:release=700[duck];
    [2:a]volume=0.16[fx];
    [voice][duck][fx]amix=inputs=3:normalize=0:duration=longest,
         loudnorm=I=-14:TP=-1.5:LRA=11[out]" \
  -map "[out]" -ar 48000 "$B/mix.wav"

ffmpeg -y -loglevel error -i "$V" -i "$B/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration,size,bit_rate -show_entries stream=codec_name,width,height,r_frame_rate -of compact "$OUT"

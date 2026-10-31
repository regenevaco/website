#!/usr/bin/env bash
# Final audio mix + mux.
#   ./mix.sh <voice_dir> <music_dir> <video_in.mp4> <video_out.mp4>
# voice_dir: narration.wav (24 kHz)   music_dir: music.wav, sfx.wav (48 kHz)
set -euo pipefail
V="$1"; M="$2"; IN="$3"; OUT="$4"
MIX="$M/final_mix.wav"
ffmpeg -y -loglevel error -i "$V/narration.wav" -i "$M/music.wav" -i "$M/sfx.wav" -filter_complex "
  [0:a]aresample=48000,highpass=f=75,lowpass=f=15000,deesser=i=0.35,
       acompressor=threshold=-22dB:ratio=2.8:attack=6:release=140:makeup=2,
       equalizer=f=180:t=q:w=1:g=1.5,equalizer=f=3200:t=q:w=1.4:g=2.2,
       pan=stereo|c0=c0|c1=c0,asplit=2[voice][key];
  [1:a]volume=0.13[m];
  [m][key]sidechaincompress=threshold=0.04:ratio=3.5:attack=80:release=900:makeup=1[duck];
  [2:a]volume=0.32[fx];
  [voice][duck][fx]amix=inputs=3:normalize=0:duration=longest,
       loudnorm=I=-14:TP=-1.5:LRA=11[out]" -map "[out]" -ar 48000 -c:a pcm_s24le "$MIX"
ffmpeg -y -loglevel error -i "$IN" -i "$MIX" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k \
  -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of compact "$OUT"

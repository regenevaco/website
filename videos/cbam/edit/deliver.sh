#!/usr/bin/env bash
# Package the CBAM master for download (each file under the 400 MiB attachment limit, no re-encoding):
#   - the master split into byte parts, plus Windows/Mac join scripts and a SHA-256 to verify the rebuilt file
#   - the same video as playable 4K clips cut at keyframes (each opens on its own)
#   ./deliver.sh <master.mp4> <out_dir> <name>
set -euo pipefail
M="$1"; OUT="$2"; NAME="$3"
LIMIT=$((395 * 1024 * 1024))
mkdir -p "$OUT/parts" "$OUT/clips"

# 1) byte parts + join scripts
split -b "$LIMIT" -d -a 2 --numeric-suffixes=1 "$M" "$OUT/parts/$NAME.mp4.part"
PARTS=$(cd "$OUT/parts" && ls "$NAME".mp4.part* | sort)
SHA=$(sha256sum "$M" | cut -d' ' -f1)
{
  echo "@echo off"
  echo "rem Rebuilds $NAME.mp4 from its parts (all parts must be in this folder)."
  echo 'cd /d "%~dp0"'
  printf 'copy /b '; first=1
  for p in $PARTS; do if [ $first = 1 ]; then printf '"%s"' "$p"; first=0; else printf ' + "%s"' "$p"; fi; done
  printf ' "%s.mp4"\n' "$NAME"
  echo "echo Done: $NAME.mp4"
  echo "certutil -hashfile \"$NAME.mp4\" SHA256"
  echo "pause"
} | sed 's/$/\r/' > "$OUT/parts/JOIN-ON-WINDOWS.bat"
cp "$OUT/parts/JOIN-ON-WINDOWS.bat" "$OUT/parts/JOIN-ON-WINDOWS-rename-to-bat.txt"
cat > "$OUT/parts/JOIN-ON-MAC.command" <<EOF
#!/bin/bash
# Rebuilds $NAME.mp4 from its parts (all parts must be in this folder).
cd "\$(dirname "\$0")" || exit 1
cat $NAME.mp4.part* > $NAME.mp4 && echo "Done: $NAME.mp4"
shasum -a 256 $NAME.mp4
EOF
chmod +x "$OUT/parts/JOIN-ON-MAC.command"
printf 'SHA-256 of %s.mp4 (the rebuilt file must match):\n%s\n' "$NAME" "$SHA" > "$OUT/parts/CHECKSUM-SHA256.txt"

# 2) playable clips: cut at keyframes near equal-size boundaries
SIZE=$(stat -c %s "$M"); DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$M")
N=$(( (SIZE + LIMIT - 1) / LIMIT + 1 ))
python3 - "$M" "$OUT/clips" "$NAME" "$DUR" "$N" <<'PY'
import subprocess, sys
m, out, name, dur, n = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), int(sys.argv[5])
kf = [float(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-skip_frame", "nokey",
      "-show_entries", "frame=pts_time", "-of", "csv=p=0", m], capture_output=True, text=True).stdout.split()]
cuts = [0.0] + [min(kf, key=lambda k: abs(k - dur * i / n)) for i in range(1, n)] + [dur]
for i in range(n):
    a, b = cuts[i], cuts[i + 1]
    o = f"{out}/{name}_clip{i + 1:02d}of{n:02d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-i", m, "-t", f"{b - a:.3f}",
                    "-c", "copy", "-avoid_negative_ts", "make_zero", "-movflags", "+faststart", o], check=True)
    print(o, f"{a:.1f}-{b:.1f}s")
PY
ls -la "$OUT/parts" "$OUT/clips"

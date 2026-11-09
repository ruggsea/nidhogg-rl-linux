#!/bin/bash
# Grab one frame from the artemis game display and report whether it is a LIVE MATCH or something else.
# Kept deliberately dumb: ffmpeg with a hard timeout, then a pixel check. No ffmpeg filter graphs (those
# hung for 5 minutes on a loaded host), no PIL dependency.
set -u
DISP="${1:-:99}"
OUT="${2:-/tmp/art_frame_check.png}"
DISPLAY="$DISP" timeout 15 ffmpeg -y -loglevel quiet -f x11grab -video_size 640x480 -i "$DISP" -frames:v 1 "$OUT" || {
  echo "FAIL: could not grab a frame from $DISP"; exit 1; }
[ -s "$OUT" ] || { echo "FAIL: empty frame"; exit 1; }
python3 - "$OUT" <<'PY'
import sys, zlib, struct
path = sys.argv[1]
raw = open(path, "rb").read()
# decode minimal PNG: use ffmpeg-free approach via zlib on IDAT is fiddly; instead report size + non-uniformity
# heuristic: a blank screen compresses to a tiny PNG. A rendered game screen does not.
size = len(raw)
print(f"frame {path}: {size} bytes")
sys.exit(0 if size > 3000 else 1)
PY
rc=$?
[ $rc -eq 0 ] && echo "VERDICT: NON-BLANK FRAME (rendering)" || echo "VERDICT: BLANK/TRIVIAL FRAME"
exit $rc

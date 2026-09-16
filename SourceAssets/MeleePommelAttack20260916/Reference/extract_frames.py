"""Extract reference frames around the user-specified attack in BV1hCJFzQEyR.

User request (2026-09-16): the attack at 1:40-1:41 is the reference for a fourth
combo hit that strikes forward with the sword's counterweight (配重锤).
Usage: python extract_frames.py [start_seconds] [end_seconds]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

P = Path(__file__).parent
FRAMES = P / 'frames'
FRAMES.mkdir(exist_ok=True)
VIDEO = next(P.glob('BV1hCJFzQEyR*.mp4'))

start = float(sys.argv[1]) if len(sys.argv) > 1 else 98.6
end = float(sys.argv[2]) if len(sys.argv) > 2 else 102.0

cap = cv2.VideoCapture(str(VIDEO))
fps = cap.get(cv2.CAP_PROP_FPS)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print('video %s  %.4f fps  %d frames  %dx%d  %.3f s' % (
    VIDEO.name, fps, total, width, height, total / fps if fps else 0.0))

first = int(round(start * fps))
last = int(round(end * fps))
cap.set(cv2.CAP_PROP_POS_FRAMES, first)
saved = []
for index in range(first, min(last, total - 1) + 1):
    ok, frame = cap.read()
    if not ok:
        break
    seconds = index / fps
    name = 'f%05d_t%08.4f.png' % (index, seconds)
    cv2.imwrite(str(FRAMES / name), frame)
    saved.append((seconds, name))
cap.release()

print('saved %d frames into %s' % (len(saved), FRAMES))
for seconds, name in saved:
    print('  %.4f  %s' % (seconds, name))

"""Track the white crossguard hook (upper quillon tip) by template matching: py -3.11 track_hook.py DIR [x0 y0 x1 y1]

The template is cut from the settled hold frame f06720 (112.000 s) around the hook. Writes DIR/hook_track.json with the
best match centre (full 1920x1080 pixels) and its normalised correlation for every *.jpg in DIR.
"""
import json
import sys
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
REF = cv2.imread(str(HERE / 'frames' / 'f06720.jpg'))
TEMPLATE = REF[655:735, 525:645]           # hook tips with a little bright guard below
directory = Path(sys.argv[1])
x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6]) if len(sys.argv) >= 6 else (300, 380, 1500, 1000)
out = {}
for f in sorted(directory.glob('*.jpg')):
    img = cv2.imread(str(f))
    region = img[y0:y1, x0:x1]
    res = cv2.matchTemplate(region, TEMPLATE, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(res)
    cx, cy = x0 + loc[0] + TEMPLATE.shape[1] / 2, y0 + loc[1] + TEMPLATE.shape[0] / 2
    out[f.stem] = {'hook': [round(cx, 1), round(cy, 1)], 'score': round(float(score), 3)}
(directory / 'hook_track.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('HOOK_TRACK', len(out))

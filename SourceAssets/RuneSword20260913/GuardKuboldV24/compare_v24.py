"""Side-by-side sheet: reference frame (left) and V24 render (right) per pair, with the measured blade base marked.
py -3.11 compare_v24.py <render_dir> <out.jpg> <action> ref_frame:clip_frame [ref_frame:clip_frame ...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
render_dir, out, action = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
rows = []
for pair in sys.argv[4:]:
    ref_f, clip_f = (int(v) for v in pair.split(':'))
    ref = cv2.resize(cv2.imread(str(HERE / 'Reference' / 'frames' / ('f%05d.jpg' % ref_f))), (960, 540))
    ours = cv2.imread(str(render_dir / ('%s_f%04d.png' % (action, clip_f))))
    for img in (ref, ours):
        for x in range(0, 960, 50):
            cv2.line(img, (x, 0), (x, 540), (60, 60, 60) if x % 250 else (0, 120, 120), 1)
        for y in range(0, 540, 50):
            cv2.line(img, (0, y), (960, y), (60, 60, 60) if y % 250 else (0, 120, 120), 1)
    cv2.putText(ref, 'reference %.3f s' % (ref_f / 60.0), (10, 525), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)
    cv2.putText(ours, 'V24 %s %.3f s' % (action, clip_f / 120.0), (10, 525), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)
    rows.append(np.hstack([ref, ours]))
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(out)

"""Render a fitted pose and compose it with the reference still (side by side + 50 % overlay).

python -I quick_view.py [fit json, default Work/fit_idle.json] [tag]
Output: Work/view_<tag>.jpg (reference | ours) and Work/view_<tag>_overlay.jpg
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from dual_rig import DualRig  # noqa: E402

BLENDER = r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
REF = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\DualKukriBV19dUqBJECT20261025\idle_frames\f00105.png")


def grid(im):
    h, w = im.shape[:2]
    for i in range(-10, 11, 2):
        x, y = int((i / 10 + 1) * w / 2), int((i / 10 + 1) * h / 2)
        c = (0, 255, 255) if i % 10 == 0 else (0, 140, 255)
        cv2.line(im, (x, 0), (x, h), c, 1)
        cv2.line(im, (0, y), (w, y), c, 1)
    return im


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else P / 'Work' / 'fit_idle.json'
    tag = sys.argv[2] if len(sys.argv) > 2 else 'fit'
    fit = json.loads(src.read_text('utf-8'))
    right = fit['right']
    left = fit.get('left_mirrored') or fit['left']
    D = DualRig()
    world, Kr, Kl, info = D.pose(right, left)
    out = P / 'Work' / 'render'
    poses = {'poses': {tag: {'bones': {n: t.pack() for n, t in world.items()}, 'kukri_r': Kr.pack(), 'kukri_l': Kl.pack()}}}
    pj = out / (tag + '.json')
    out.mkdir(parents=True, exist_ok=True)
    pj.write_text(json.dumps(poses), encoding='utf-8')
    res = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', str(P / 'render_idle.py'), '--', str(pj), str(out), '960'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0 or 'DUAL_PREVIEW' not in res.stdout:
        print(res.stdout[-3000:], res.stderr[-3000:])
        sys.exit(1)
    ours = cv2.imread(str(out / (tag + '.png')))
    ref = cv2.resize(cv2.imread(str(REF)), (ours.shape[1], ours.shape[0]), interpolation=cv2.INTER_AREA)
    side = np.hstack([grid(ref.copy()), grid(ours.copy())])
    cv2.imwrite(str(P / 'Work' / ('view_%s.jpg' % tag)), side, [cv2.IMWRITE_JPEG_QUALITY, 90])
    over = cv2.addWeighted(ref, 0.5, ours, 0.5, 0)
    cv2.imwrite(str(P / 'Work' / ('view_%s_overlay.jpg' % tag)), grid(over), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print('left hand err %.4f cm' % info['left_hand_err_cm'])


if __name__ == '__main__':
    main()

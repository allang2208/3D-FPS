"""Render a sprint-hold fit next to the reference sprint still (17.50 s) plus two outside views of the arms.

python -I view_run.py <fit json> <tag>     -> Work/view_<tag>.jpg (reference | ours | 50 % overlay, NDC grid every 0.2)
                                              and Work/view_<tag>_side.jpg (from the right / from above-left)
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
from kmath import mesh_to_cam  # noqa: E402
from quick_view import BLENDER, grid  # noqa: E402

REF = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\DualKukriBV19dUqBJECT20261025\run_frames\f00525.png")


def main():
    fit = json.loads(Path(sys.argv[1]).read_text('utf-8'))
    tag = sys.argv[2]
    D = DualRig()
    world, Kr, Kl, info = D.pose(fit['right'], fit['left_mirrored'])
    base = dict(bones={n: t.pack() for n, t in world.items()}, kukri_r=Kr.pack(), kukri_l=Kl.pack())
    gl, gr = mesh_to_cam(Kl.p), mesh_to_cam(Kr.p)
    mid = ((gl + gr) / 2).tolist()
    views = {'eye': None,
             'right': dict(loc=[mid[0] + 5, 95, mid[2] + 5], look=mid, fov=60),
             'above': dict(loc=[-35, -25, 75], look=mid, fov=60)}
    poses = {'%s_%s' % (tag, k): dict(base, **({'camera': v} if v else {})) for k, v in views.items()}
    out = P / 'Work' / 'render'
    out.mkdir(parents=True, exist_ok=True)
    pj = out / (tag + '_views.json')
    pj.write_text(json.dumps(dict(poses=poses)), encoding='utf-8')
    res = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', str(P / 'render_idle.py'), '--', str(pj), str(out), '960'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0 or res.stdout.count('DUAL_PREVIEW') < len(poses):
        print(res.stdout[-3000:], res.stderr[-3000:])
        sys.exit(1)
    ours = cv2.imread(str(out / ('%s_eye.png' % tag)))
    ref = cv2.resize(cv2.imread(str(REF)), (ours.shape[1], ours.shape[0]), interpolation=cv2.INTER_AREA)
    over = cv2.addWeighted(ref, 0.5, ours, 0.5, 0)
    cv2.imwrite(str(P / 'Work' / ('view_%s.jpg' % tag)), np.vstack([grid(ref.copy()), grid(ours.copy()), grid(over)]),
                [cv2.IMWRITE_JPEG_QUALITY, 90])
    side = np.hstack([cv2.imread(str(out / ('%s_%s.png' % (tag, k)))) for k in ('right', 'above')])
    cv2.imwrite(str(P / 'Work' / ('view_%s_side.jpg' % tag)), side, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print('left hand err %.4f cm' % info['left_hand_err_cm'])


if __name__ == '__main__':
    main()

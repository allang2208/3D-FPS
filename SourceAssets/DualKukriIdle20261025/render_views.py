"""Hold renders for review: eye view, both grips close up, overhead and outside views, and the reference comparison.

python -I render_views.py [--blend]
Output: Previews/hold_*.png, Previews/compare.jpg (reference | ours, NDC grid every 0.2), Previews/overlay.jpg,
        Previews/details.jpg; --blend also saves Previews/hold_eye.blend (editable, textures not packed).
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
from quick_view import BLENDER, REF, grid  # noqa: E402


def main():
    keys = json.loads((P / 'pose_keys.json').read_text('utf-8'))
    D = DualRig()
    world, Kr, Kl, _ = D.pose(keys['right'], keys['left_mirrored'])
    gl, gr = mesh_to_cam(Kl.p).tolist(), mesh_to_cam(Kr.p).tolist()
    mid = [(a + b) / 2 for a, b in zip(gl, gr)]
    views = {
        'eye': None,
        'grip_l': dict(loc=[0, 0, 0], look=gl, fov=22),
        'grip_r': dict(loc=[0, 0, 0], look=gr, fov=18),
        'top': dict(loc=[-20, 0, 50], look=[mid[0], mid[1], mid[2]], fov=70),
        'outside_l': dict(loc=[mid[0] + 10, -75, mid[2] + 15], look=mid, fov=55),
        'below': dict(loc=[mid[0] + 45, mid[1], mid[2] - 45], look=mid, fov=60),
    }
    base = dict(bones={n: t.pack() for n, t in world.items()}, kukri_r=Kr.pack(), kukri_l=Kl.pack())
    poses = {('hold_' + k): dict(base, **({'camera': v} if v else {})) for k, v in views.items()}
    out = P / 'Previews'
    out.mkdir(exist_ok=True)
    pj = P / 'Work' / 'render' / 'hold_views.json'
    pj.parent.mkdir(parents=True, exist_ok=True)
    pj.write_text(json.dumps(dict(poses=poses)), encoding='utf-8')
    cmd = [BLENDER, '-b', '--factory-startup', '--python', str(P / 'render_idle.py'), '--', str(pj), str(out), '1280']
    if '--blend' in sys.argv:
        cmd.append('--blend')
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0 or res.stdout.count('DUAL_PREVIEW') < len(poses):
        print(res.stdout[-3000:], res.stderr[-3000:])
        sys.exit(1)
    eye = cv2.imread(str(out / 'hold_eye.png'))
    ref = cv2.resize(cv2.imread(str(REF)), (eye.shape[1], eye.shape[0]), interpolation=cv2.INTER_AREA)
    lab = lambda im, s: cv2.putText(im, s, (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2) is not None and im
    cv2.imwrite(str(out / 'compare.jpg'), np.vstack([lab(grid(ref.copy()), 'reference 3.50 s'), lab(grid(eye.copy()), 'dual kukri hold')]),
                [cv2.IMWRITE_JPEG_QUALITY, 90])
    cv2.imwrite(str(out / 'overlay.jpg'), grid(cv2.addWeighted(ref, 0.5, eye, 0.5, 0)), [cv2.IMWRITE_JPEG_QUALITY, 90])
    tiles = [lab(cv2.resize(cv2.imread(str(out / ('hold_%s.png' % k))), (640, 360)), k) for k in views if k != 'eye']
    tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(out / 'details.jpg'), np.vstack([np.hstack(tiles[0:3]), np.hstack(tiles[3:6])]), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print('rendered', ', '.join(poses))


if __name__ == '__main__':
    main()
